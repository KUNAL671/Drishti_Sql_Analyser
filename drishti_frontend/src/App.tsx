import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { PageId, DatasetItem } from './types';
import { fetchDatasets, getBackendConfig, dispatchQueryToBackend } from './services/backendApi';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { NewAnalysisView } from './components/NewAnalysisView';
import { AnalysisRunningView } from './components/AnalysisRunningView';
import { AnalysisResultView } from './components/AnalysisResultView';
import { DatasetsView } from './components/DatasetsView';
import { SchemaExplorerView } from './components/SchemaExplorerView';
import { QueryHistoryView } from './components/QueryHistoryView';
import { SettingsView } from './components/SettingsView';
import { SearchModal } from './components/SearchModal';

export function App() {
  const [activePage, setActivePage] = useState<PageId>('new-analysis');
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [activeDatasetId, setActiveDatasetId] = useState<string>('default');
  const [activeDatasetName, setActiveDatasetName] = useState<string>('Select a dataset');
  const [currentQuery, setCurrentQuery] = useState<string>('');
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [conversationId, setConversationId] = useState<string | undefined>();

  const loadDatasets = async () => {
    const config = getBackendConfig();
    const backendDs = await fetchDatasets(config);
    const mapped: DatasetItem[] = backendDs.map(ds => ({
      id: ds.dataset_id,
      title: ds.dataset_name,
      tablePath: ds.table_name,
      type: (ds.file_type || '').toUpperCase(),
      status: ds.dataset_status,
      activeInSession: false,
      rows: `${(ds.row_count || 0).toLocaleString()} rows`,
      columns: ds.column_count || 0,
      size: 'N/A',
      qualityScore: ds.quality_report && ds.quality_report.length ? `${ds.quality_report.length} checks run` : 'Pending',
      validationPct: 100,
      updatedAt: new Date(ds.created_at).toLocaleDateString()
    }));
    
    if (mapped.length > 0) {
      if (!mapped.find(d => d.id === activeDatasetId)) {
        setActiveDatasetId(mapped[0].id);
        setActiveDatasetName(mapped[0].title);
        mapped[0].activeInSession = true;
      } else {
        const active = mapped.find(d => d.id === activeDatasetId);
        if (active) active.activeInSession = true;
      }
    }
    setDatasets(mapped);
  };

  useEffect(() => {
    loadDatasets();
  }, []);
  const [isAnalysisRunning, setIsAnalysisRunning] = useState<boolean>(false);
  const [isResultReady, setIsResultReady] = useState<boolean>(false);
  const [isSearchOpen, setIsSearchOpen] = useState<boolean>(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);

  const [apiPromise, setApiPromise] = useState<Promise<any> | null>(null);

  // Handler to start analysis from a query
  const handleStartAnalysis = (query: string) => {
    setCurrentQuery(query);
    setIsAnalysisRunning(true);
    setIsResultReady(false);
    setActivePage('workspace-and-analysis');

    const config = getBackendConfig();
    const p = dispatchQueryToBackend(query, config, activeDatasetId, conversationId).then(res => {
      setAnalysisResult(res);
      if (res?.conversation_id) {
        setConversationId(res.conversation_id);
      }
      return res;
    }).catch(err => {
      console.error(err);
      return null;
    });
    setApiPromise(p);
  };

  // Handler when 7-stage analysis completes
  const handleAnalysisComplete = async () => {
    if (apiPromise) {
      await apiPromise; // wait for backend to finish
    }
    setIsAnalysisRunning(false);
    setIsResultReady(true);
  };

  // Handler to reset and start a fresh question
  const handleNewQuestion = () => {
    setIsAnalysisRunning(false);
    setIsResultReady(false);
    setAnalysisResult(null);
    setConversationId(undefined);
    setActivePage('new-analysis');
  };

  return (
    <div className="min-h-screen bg-surface text-on-surface flex font-sans antialiased selection:bg-primary-container/30 selection:text-primary overflow-x-hidden">
      {/* 1. Collapsible Sidebar (Minimise / Extract) */}
      <Sidebar
        activePage={activePage}
        onSelectPage={(page) => {
          setActivePage(page);
          if (page === 'new-analysis') {
            setIsAnalysisRunning(false);
            setIsResultReady(false);
          }
        }}
        activeDatasetName={activeDatasetName}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
      />

      {/* 2. Top Navigation Header */}
      <Header
        activePage={activePage}
        onNewQuestion={handleNewQuestion}
        onOpenSearch={() => setIsSearchOpen(true)}
        activeDatasetName={activeDatasetName}
        currentQuery={currentQuery}
        isSidebarCollapsed={isSidebarCollapsed}
      />

      {/* 3. Main Workspace Content Area */}
      <main
        className={`pt-16 flex-1 min-h-screen relative flex flex-col items-center transition-all duration-300 ease-in-out ${
          isSidebarCollapsed ? 'ml-20' : 'ml-72'
        }`}
      >
        <AnimatePresence mode="wait">
          {/* View 1: New Analysis Landing Console */}
          {activePage === 'new-analysis' && (
            <motion.div
              key="new-analysis-view"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.35, ease: 'easeInOut' }}
              className="w-full flex justify-center"
            >
              <NewAnalysisView
                onStartAnalysis={handleStartAnalysis}
                activeDatasetName={activeDatasetName}
                onSelectDataset={(name, id) => {
                  setActiveDatasetName(name);
                  if (id) setActiveDatasetId(id);
                }}
                availableDatasets={datasets}
                onUploadNewDataset={() => setActivePage('datasets')}
                onNavigateToSchema={() => setActivePage('schema-explorer')}
              />
            </motion.div>
          )}

          {/* View 2: Workspace & Analysis (Running pipeline OR Verified Result) */}
          {activePage === 'workspace-and-analysis' && (
            <motion.div
              key="workspace-view"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.35, ease: 'easeInOut' }}
              className="w-full flex justify-center"
            >
              {isAnalysisRunning ? (
                <AnalysisRunningView
                  userQuery={currentQuery}
                  onComplete={handleAnalysisComplete}
                  targetDataset={activeDatasetName}
                />
              ) : isResultReady ? (
                <AnalysisResultView
                  userQuery={currentQuery}
                  onNewAnalysis={handleNewQuestion}
                  onNavigateToSchema={() => setActivePage('schema-explorer')}
                  isSidebarCollapsed={isSidebarCollapsed}
                  activeDatasetName={activeDatasetName}
                  activeDatasetId={activeDatasetId}
                  backendResult={analysisResult}
                  onStartAnalysis={handleStartAnalysis}
                />
              ) : (
                /* Fallback if user navigates to workspace directly without active run */
                <AnalysisResultView
                  userQuery={currentQuery}
                  onNewAnalysis={handleNewQuestion}
                  onNavigateToSchema={() => setActivePage('schema-explorer')}
                  isSidebarCollapsed={isSidebarCollapsed}
                  activeDatasetName={activeDatasetName}
                  activeDatasetId={activeDatasetId}
                  backendResult={analysisResult}
                  onStartAnalysis={handleStartAnalysis}
                />
              )}
            </motion.div>
          )}

          {/* View 3: Datasets Catalog */}
          {activePage === 'datasets' && (
            <motion.div
              key="datasets-view"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.35, ease: 'easeInOut' }}
              className="w-full flex justify-center"
            >
              <DatasetsView
                datasets={datasets}
                onDatasetsChange={(newDs) => setDatasets(newDs)}
                onSelectDataset={(name, id) => {
                  setActiveDatasetName(name);
                  if (id) setActiveDatasetId(id);
                }}
                onNewAnalysisWithDataset={(name, id) => {
                  setActiveDatasetName(name);
                  if (id) setActiveDatasetId(id);
                  handleNewQuestion();
                }}
                onDatasetUploaded={loadDatasets}
              />
            </motion.div>
          )}

          {/* View 4: Schema Explorer & AST Mapping */}
          {activePage === 'schema-explorer' && (
            <motion.div
              key="schema-explorer-view"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.35, ease: 'easeInOut' }}
              className="w-full flex justify-center"
            >
              <SchemaExplorerView
                onNewQueryWithColumn={(colQuery) => handleStartAnalysis(colQuery)}
              />
            </motion.div>
          )}

          {/* View 5: Query Execution History */}
          {activePage === 'query-history' && (
            <motion.div
              key="history-view"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.35, ease: 'easeInOut' }}
              className="w-full flex justify-center"
            >
              <QueryHistoryView
                onRestoreQuery={(restoredQuery) => handleStartAnalysis(restoredQuery)}
                onNavigateHome={() => setActivePage('new-analysis')}
                onViewAnalysis={(analysisId, resultData) => {
                  setAnalysisResult(resultData);
                  setConversationId(resultData.conversation_id);
                  if (resultData.dataset_id && resultData.dataset_id !== activeDatasetId) {
                    setActiveDatasetId(resultData.dataset_id);
                    setActiveDatasetName(resultData.dataset_name || 'Historical Dataset');
                  } else if (!resultData.dataset_id && activeDatasetId !== 'default') {
                    // Fallback for older queries without dataset_id
                    setActiveDatasetId('default');
                    setActiveDatasetName('NYC Yellow Taxi');
                  }
                  setCurrentQuery(resultData.question);
                  setIsResultReady(true);
                  setIsAnalysisRunning(false);
                  
                  // Use setTimeout to allow state flush before navigating to the result view,
                  // preventing the context integrity check mismatch during transition
                  setTimeout(() => {
                    setActivePage('workspace-and-analysis');
                  }, 0);
                }}
              />
            </motion.div>
          )}

          {/* View 6: Console & Safety Settings */}
          {activePage === 'settings' && (
            <motion.div
              key="settings-view"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.35, ease: 'easeInOut' }}
              className="w-full flex justify-center"
            >
              <SettingsView />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* 4. Global ⌘K Quick Search & Command Modal */}
      <SearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onSelectQuery={(q) => handleStartAnalysis(q)}
      />
    </div>
  );
}

export default App;
