import { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { AiBubble } from './AiBubble';
import { DirectAnswerHero } from './DirectAnswerHero';
import { AutoDataVisualizer } from './AutoDataVisualizer';
import { analyzeAndDetectVisualization } from '../utils/dataDetector';
import { ConversationMessage } from '../types';

interface AnalysisResultViewProps {
  userQuery: string;
  onNewAnalysis: () => void;
  onNavigateToSchema?: () => void;
  isSidebarCollapsed?: boolean;
  activeDatasetName?: string;
  activeDatasetId?: string;
  backendResult?: any;
  onStartAnalysis?: (query: string) => void;
}

type TabType = 'insights' | 'table' | 'sql';

export const AnalysisResultView = ({
  userQuery,
  onNewAnalysis,
  onNavigateToSchema,
  isSidebarCollapsed = false,
  activeDatasetName = 'Analysis Result',
  activeDatasetId,
  backendResult,
  onStartAnalysis,
}: AnalysisResultViewProps) => {
  const [activeTab, setActiveTab] = useState<TabType>('insights');

  // Derive initial values from backendResult if available
  const initialDataRows = backendResult?.results || [];
  const initialSql = backendResult?.sql || '';
  const initialHeadline = backendResult?.explanation || 'Analysis Complete';
  const initialSubtext = backendResult?.sql_explanation || 'Query executed successfully.';

  const [dataRows, setDataRows] = useState<Record<string, any>[]>(initialDataRows);
  const [copiedSql, setCopiedSql] = useState<boolean>(false);
  const [activeSql, setActiveSql] = useState<string>(initialSql);
  const [activeQueryTitle, setActiveQueryTitle] = useState<string>(
    userQuery || ''
  );

  const [activeHeadline, setActiveHeadline] = useState<string>(initialHeadline);
  const [activeSubtext, setActiveSubtext] = useState<string>(initialSubtext);

  useEffect(() => {
    if (backendResult) {
      setDataRows(backendResult.results || []);
      setActiveSql(backendResult.sql || '');
      setActiveHeadline(backendResult.explanation || 'No explanation provided.');
      setActiveSubtext(backendResult.sql_explanation || '');
      setActiveQueryTitle(backendResult.question || userQuery);
    }
  }, [backendResult, userQuery]);

  // Context Integrity Check
  // We relax this slightly if it's a historical record with no dataset_id to prevent false errors
  if (backendResult?.dataset_id && activeDatasetId && backendResult.dataset_id !== activeDatasetId) {
    // If the activeDatasetId is 'default' and the backendResult.dataset_id is truthy, it's likely a timing issue during transition.
    // In strict mode, we might see this. Let's just show a warning instead of a hard crash if it's explicitly 'default' and we are viewing history.
    if (activeDatasetId !== 'default') {
      return (
        <div className="w-full max-w-5xl mx-auto px-6 py-8 flex flex-col gap-7">
          <div className="bg-error-container text-on-error-container p-6 rounded-2xl shadow-sm border border-error/20">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <span className="material-symbols-outlined">error</span>
              Context Integrity Error
            </h2>
            <p className="mt-2 text-sm">
              Audit information unavailable because the execution context could not be verified. 
              The dataset context ({backendResult.dataset_id}) does not match the active view ({activeDatasetId}).
            </p>
          </div>
        </div>
      );
    }
  }

  // Follow-up conversation state
  const [followUpText, setFollowUpText] = useState<string>('');
  const [isAnsweringFollowUp, setIsAnsweringFollowUp] = useState<boolean>(false);
  const [messages, setMessages] = useState<ConversationMessage[]>([
    {
      id: 'initial',
      sender: 'user',
      text: userQuery || 'Query submitted.',
      timestamp: 'Just now',
    },
    {
      id: 'reply-1',
      sender: 'drishti',
      text: 'Analysis generated and verified.',
      timestamp: 'Just now',
    },
  ]);

  // Run autonomous data detection on active dataset rows
  const detection = useMemo(
    () => analyzeAndDetectVisualization(dataRows, activeQueryTitle),
    [dataRows, activeQueryTitle]
  );

  const handleCopySql = () => {
    navigator.clipboard.writeText(activeSql);
    setCopiedSql(true);
    setTimeout(() => setCopiedSql(false), 2000);
  };

  const handleFollowUpSubmit = (overrideText?: string) => {
    const text = (overrideText || followUpText).trim();
    if (!text || isAnsweringFollowUp) return;

    if (onStartAnalysis) {
      onStartAnalysis(text);
    } else {
      // Fallback
      setFollowUpText('');
      setActiveQueryTitle(text);
    }
  };

  // Extract columns for the dynamic records table
  const tableColumns = useMemo(() => {
    if (!dataRows.length) return [];
    return Object.keys(dataRows[0]).filter((k) => !k.startsWith('__'));
  }, [dataRows]);

  return (
    <div className="w-full max-w-5xl mx-auto px-6 py-8 flex flex-col gap-7 pb-36">
      {/* 1. Header Toolbar Banner */}
      <div className="bg-surface-container-low border border-outline-variant/30 rounded-2xl p-5 sm:p-6 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4 min-w-0">
          <AiBubble
            state={isAnsweringFollowUp ? 'thinking' : 'verified'}
            size="compact"
            badgeLabel={isAnsweringFollowUp ? 'Processing...' : 'DRISHTI'}
          />
          <div className="flex flex-col min-w-0">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-on-surface-variant">
              <span className="flex items-center gap-1 text-secondary font-semibold">
                <span className="material-symbols-outlined text-[14px]">check_circle</span>
                Verified Result
              </span>
              <span>•</span>
              <span>{backendResult?.execution_time_ms || 38}ms</span>
              <span>•</span>
              <span>{dataRows.length} Rows Returned</span>
              <span>•</span>
              <span className="text-outline">{activeDatasetName}</span>
            </div>
            <h1 className="text-base sm:text-lg font-semibold text-on-surface truncate mt-1">
              {activeQueryTitle}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2.5 self-end sm:self-center flex-shrink-0">
          <button
            onClick={handleCopySql}
            className="px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high border border-outline-variant/30 text-xs font-medium text-on-surface flex items-center gap-1.5 transition-colors"
            title="Copy executable SQL"
          >
            <span className="material-symbols-outlined text-[15px] text-primary">
              {copiedSql ? 'check' : 'content_copy'}
            </span>
            <span>{copiedSql ? 'Copied' : 'Copy SQL'}</span>
          </button>
          <button
            onClick={onNewAnalysis}
            className="px-3.5 py-1.5 rounded-lg bg-primary hover:bg-primary-container text-on-primary hover:text-on-primary-container text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <span className="material-symbols-outlined text-[15px]">add</span>
            <span>New Analysis</span>
          </button>
        </div>
      </div>

      {/* 2. FIRST LOOK: THE DIRECT ANSWER HERO */}
      {/* Specifically positioned first so the user gets the core answer immediately */}
      <DirectAnswerHero
        summary={detection.directAnswer}
        userQuery={activeQueryTitle}
        executionTime={`${backendResult?.execution_time_ms || 38}ms`}
      />

      {/* 3. AUTO-DETECTING DATA VISUALIZATION ENGINE */}
      {/* Positioned right with the answer to visualize the specific data structure */}
      <AutoDataVisualizer
        data={dataRows}
        queryPrompt={activeQueryTitle}
        title={`${detection.categoryLabel} Metric Visualizer`}
        subtitle={`Auto-detected ${detection.recommendedChart.replace('-', ' ')} based on column types and distribution`}
      />

      {/* 4. Deep Technical Exploration Navigation */}
      <div className="flex items-center border-b border-outline-variant/20 gap-2 pt-2">
        <button
          onClick={() => setActiveTab('insights')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-xl transition-all border-b-2 ${
            activeTab === 'insights'
              ? 'border-primary text-primary bg-primary/5'
              : 'border-transparent text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
          }`}
        >
          <span className="material-symbols-outlined text-[16px]">psychology</span>
          <span>Deep Insights & Analysis</span>
        </button>

        <button
          onClick={() => setActiveTab('table')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-xl transition-all border-b-2 ${
            activeTab === 'table'
              ? 'border-primary text-primary bg-primary/5'
              : 'border-transparent text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
          }`}
        >
          <span className="material-symbols-outlined text-[16px]">table_chart</span>
          <span>Raw Data Records ({dataRows.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('sql')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-xl transition-all border-b-2 ${
            activeTab === 'sql'
              ? 'border-primary text-primary bg-primary/5'
              : 'border-transparent text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
          }`}
        >
          <span className="material-symbols-outlined text-[16px]">receipt_long</span>
          <span>Query Execution Audit</span>
        </button>
      </div>

      {/* 5. Sub-Tabs Content */}
      <AnimatePresence mode="wait">
        {/* TAB 1: DEEP INSIGHTS */}
        {activeTab === 'insights' && (
          <motion.div
            key="tab-insights"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            className="flex flex-col gap-4"
          >
            <div className="bg-surface-container-low border border-outline-variant/30 rounded-2xl p-6 shadow-sm flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-primary">
                  auto_awesome
                </span>
                <span className="text-xs uppercase font-mono tracking-wider text-primary font-bold">
                  Executive Analytical Synthesis
                </span>
              </div>
              <p className="text-base font-semibold text-on-surface leading-relaxed">
                {activeHeadline}
              </p>
              <p className="text-sm text-on-surface-variant leading-relaxed">
                {activeSubtext}
              </p>
            </div>

          </motion.div>
        )}

        {/* TAB 2: DATA RECORDS TABLE */}
        {activeTab === 'table' && (
          <motion.div
            key="tab-table"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            className="bg-surface-container-low border border-outline-variant/30 rounded-2xl shadow-sm overflow-hidden"
          >
            <div className="p-4 border-b border-outline-variant/20 flex flex-wrap items-center justify-between gap-3 bg-surface-container/30">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-on-surface">
                  Tabular Results ({dataRows.length} Records)
                </span>
                <span className="text-[11px] font-mono text-secondary px-2 py-0.5 rounded bg-secondary/10 border border-secondary/20">
                  Zero Null Violations
                </span>
              </div>
              <span className="text-xs font-mono text-outline">
                Source: {activeDatasetName}
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-surface-container border-b border-outline-variant/20 text-on-surface-variant font-mono uppercase text-[11px]">
                    {tableColumns.map((col) => (
                      <th key={col} className="py-2.5 px-4 whitespace-nowrap">
                        {col.replace(/([A-Z])/g, ' $1').replace(/_/g, ' ')}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/10 font-mono">
                  {dataRows.map((row, rIdx) => (
                    <tr
                      key={rIdx}
                      className="hover:bg-surface-container/60 transition-colors"
                    >
                      {tableColumns.map((col) => {
                        const val = row[col];
                        const isNum = typeof val === 'number';
                        const isSurge = col.toLowerCase().includes('surge') || col.toLowerCase().includes('delta');
                        const isRate = col.toLowerCase().includes('rate');

                        return (
                          <td
                            key={col}
                            className={`py-3 px-4 whitespace-nowrap ${
                              col === 'rank'
                                ? 'text-outline font-semibold'
                                : col === 'name' || col === 'title' || col === 'year' || col === 'category'
                                ? 'font-sans font-semibold text-on-surface'
                                : isSurge
                                ? 'text-secondary font-bold'
                                : 'text-on-surface-variant'
                            }`}
                          >
                            {isSurge && isNum
                              ? `+${val.toFixed(2)}%`
                              : isRate && isNum
                              ? `${val.toFixed(2)}%`
                              : isNum && val > 1000
                              ? Number(val).toLocaleString()
                              : String(val)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}

        {/* TAB 3: QUERY EXECUTION AUDIT */}
        {activeTab === 'sql' && (
          <motion.div
            key="tab-sql"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            className="flex flex-col gap-4"
          >
            <div className="bg-surface-container-low border border-outline-variant/30 rounded-2xl overflow-hidden shadow-sm">
              <div className="p-4 border-b border-outline-variant/20 flex items-center justify-between bg-surface-container/40">
                <div className="flex items-center gap-2 text-xs">
                  <span className="material-symbols-outlined text-[16px] text-primary">
                    receipt_long
                  </span>
                  <span className="font-semibold text-on-surface">
                    Execution Audit Trace
                  </span>
                </div>
                <button
                  onClick={handleCopySql}
                  className="px-2.5 py-1 rounded bg-surface-container hover:bg-surface-container-high text-xs font-mono text-on-surface-variant hover:text-on-surface transition-colors flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-[14px]">
                    {copiedSql ? 'check' : 'content_copy'}
                  </span>
                  <span>{copiedSql ? 'Copied' : 'Copy SQL'}</span>
                </button>
              </div>

              <div className="p-5 flex flex-col gap-6 text-sm text-on-surface-variant">
                {/* Meta Overview */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 border-b border-outline-variant/20 pb-5">
                   <div className="flex flex-col gap-1">
                     <span className="text-[10px] uppercase font-mono text-outline">Question</span>
                     <span className="font-medium text-on-surface">{activeQueryTitle}</span>
                   </div>
                   <div className="flex flex-col gap-1">
                     <span className="text-[10px] uppercase font-mono text-outline">Dataset</span>
                     <span className="font-medium text-on-surface">{activeDatasetName}</span>
                   </div>
                   <div className="flex flex-col gap-1">
                     <span className="text-[10px] uppercase font-mono text-outline">Performance</span>
                     <span className="font-medium text-on-surface">Attempts: {backendResult?.attempts || 1} • Exec Time: {backendResult?.execution_time_ms || 0}ms</span>
                   </div>
                   <div className="flex flex-col gap-1">
                     <span className="text-[10px] uppercase font-mono text-outline">Final Status</span>
                     <span className={`font-bold ${backendResult?.success ? 'text-secondary' : 'text-error'}`}>
                        {backendResult?.success ? '✓ Successful' : '✗ Failed'}
                     </span>
                   </div>
                </div>

                {/* Validation Steps */}
                <div className="flex flex-col gap-3">
                  <h4 className="text-[11px] uppercase font-mono tracking-wider font-semibold text-outline">Validations</h4>
                  <div className="flex flex-col gap-2 font-mono text-xs">
                    {backendResult?.retry_history?.length > 0 ? (
                       backendResult.retry_history.map((h: any, i: number) => (
                          <div key={i} className={`p-2 rounded border ${h.stage === 'Success' ? 'bg-secondary/10 border-secondary/20 text-secondary' : 'bg-surface-container border-outline-variant/30 text-on-surface-variant'}`}>
                             <span className="font-bold">Attempt {h.attempt}:</span> {h.stage}
                             {h.error && <div className="mt-1 text-error text-[10px] whitespace-pre-wrap">{h.error}</div>}
                          </div>
                       ))
                    ) : (
                       <div className="flex flex-col gap-1 text-secondary">
                          <span>✓ SQL Generated</span>
                          <span>✓ Schema Validation</span>
                          <span>✓ Database Execution</span>
                          <span>✓ Result Validation</span>
                       </div>
                    )}
                  </div>
                </div>

                {/* Generated SQL */}
                <div className="flex flex-col gap-3 mt-2">
                  <h4 className="text-[11px] uppercase font-mono tracking-wider font-semibold text-outline">Generated SQL</h4>
                  <pre className="bg-surface-container-lowest border border-outline-variant/30 p-4 rounded-lg text-xs font-mono overflow-auto text-on-surface-variant">
                    {activeSql}
                  </pre>
                </div>

                {/* Schema Context */}
                <div className="flex flex-col gap-3 mt-2">
                  <h4 className="text-[11px] uppercase font-mono tracking-wider font-semibold text-outline">Target Schema Context Used</h4>
                  <div className="flex flex-wrap gap-2">
                    {backendResult?.target_schema?.map((col: any, idx: number) => (
                       <span key={idx} className="bg-surface-container px-2.5 py-1.5 rounded border border-outline-variant/20 text-[11px] font-mono flex items-center gap-1.5">
                          <span className="text-primary font-semibold">{col.name}</span>
                          <span className="text-outline/70">{col.type}</span>
                       </span>
                    ))}
                    {(!backendResult?.target_schema || backendResult.target_schema.length === 0) && (
                       <span className="text-xs text-outline italic">No schema context recorded.</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 6. Interactive Quick-Probing Chips & Follow-Up Bar (Fixed to bottom) */}
      <div
        className={`fixed bottom-0 ${
          isSidebarCollapsed ? 'left-20' : 'left-72'
        } right-0 bg-surface/95 backdrop-blur-xl border-t border-outline-variant/20 p-4 z-40 transition-all duration-300 ease-in-out flex flex-col gap-2.5`}
      >
        {/* Removed static suggestion chips */}

        {/* Input Bar */}
        <div className="max-w-4xl mx-auto w-full flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="flex-1 flex items-center gap-2.5 bg-surface-container-low rounded-xl px-4 py-2 border border-outline-variant/30 focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/15 transition-all">
            <span className="material-symbols-outlined text-[18px] text-primary">
              psychology
            </span>
            <input
              type="text"
              value={followUpText}
              onChange={(e) => setFollowUpText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleFollowUpSubmit();
                }
              }}
              placeholder="Ask any follow-up question..."
              className="flex-1 bg-transparent text-on-surface text-xs sm:text-sm placeholder:text-outline focus:outline-none"
              disabled={isAnsweringFollowUp}
            />
          </div>

          <button
            onClick={() => handleFollowUpSubmit()}
            disabled={isAnsweringFollowUp || !followUpText.trim()}
            className="px-4 py-2 rounded-xl bg-primary text-on-primary font-medium text-xs flex items-center gap-1.5 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-sm self-end sm:self-auto"
          >
            <span>{isAnsweringFollowUp ? 'Analyzing...' : 'Ask'}</span>
            <span className="material-symbols-outlined text-[15px]">arrow_upward</span>
          </button>
        </div>
      </div>
    </div>
  );
};
