import { useState, useEffect, useCallback, useRef } from 'react';
import { motion } from 'motion/react';
import { fetchHistory, fetchHistoryItem, HistorySummary, getBackendConfig, BackendDataset, fetchDatasets, deleteHistoryItem } from '../services/backendApi';

interface QueryHistoryViewProps {
  onRestoreQuery: (query: string) => void;
  onViewAnalysis: (analysisId: string, resultData: any) => void;
  onNavigateHome: () => void;
}

export const QueryHistoryView = ({ onRestoreQuery, onViewAnalysis, onNavigateHome }: QueryHistoryViewProps) => {
  const [historyItems, setHistoryItems] = useState<HistorySummary[]>([]);
  const [totalItems, setTotalItems] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isError, setIsError] = useState<boolean>(false);
  const [datasets, setDatasets] = useState<BackendDataset[]>([]);

  const [search, setSearch] = useState<string>('');
  const [activeDataset, setActiveDataset] = useState<string>('all');
  const [activeStatus, setActiveStatus] = useState<string>('all');
  const [offset, setOffset] = useState<number>(0);

  // Track which analysis is currently being loaded (View button)
  const [loadingViewId, setLoadingViewId] = useState<string | null>(null);
  // Track 404 / error for View
  const [viewError, setViewError] = useState<string | null>(null);

  // Prevent duplicate initial loads in StrictMode
  const didMount = useRef(false);
  
  const LIMIT = 20;

  const loadDatasets = useCallback(async () => {
    const ds = await fetchDatasets(getBackendConfig());
    setDatasets(ds);
  }, []);

  const loadHistory = useCallback(async (reset = false, currentActiveDataset?: string, currentActiveStatus?: string, currentSearch?: string) => {
    if (reset) {
      setOffset(0);
      setIsLoading(true);
    }
    
    setIsError(false);
    const config = getBackendConfig();
    const currentOffset = reset ? 0 : offset;
    
    const dsFilter = currentActiveDataset ?? activeDataset;
    const statusFilter = currentActiveStatus ?? activeStatus;
    const searchFilter = currentSearch ?? search;
    
    const result = await fetchHistory(
      config,
      dsFilter === 'all' ? undefined : dsFilter,
      statusFilter === 'all' ? undefined : statusFilter,
      searchFilter || undefined,
      LIMIT,
      currentOffset
    );

    if (result) {
      if (reset) {
        setHistoryItems(result.items);
      } else {
        setHistoryItems(prev => [...prev, ...result.items]);
      }
      setTotalItems(result.total);
      setOffset(currentOffset + LIMIT);
    } else {
      setIsError(true);
    }
    setIsLoading(false);
  }, [offset, activeDataset, activeStatus, search]);

  // Single mount effect — load datasets + initial history once
  useEffect(() => {
    if (didMount.current) return;
    didMount.current = true;
    loadDatasets();
    loadHistory(true);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // When filters change (but NOT on initial mount)
  const isFirstFilterRender = useRef(true);
  useEffect(() => {
    if (isFirstFilterRender.current) {
      isFirstFilterRender.current = false;
      return;
    }
    loadHistory(true, activeDataset, activeStatus, search);
  }, [activeDataset, activeStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadHistory(true, activeDataset, activeStatus, search);
  };

  const handleView = async (analysisId: string) => {
    // Prevent duplicate clicks
    if (loadingViewId) return;

    console.log("[History] View clicked", analysisId);
    setLoadingViewId(analysisId);
    setViewError(null);

    try {
      const config = getBackendConfig();
      const detail = await fetchHistoryItem(config, analysisId);
      console.log("[History] Detail response", detail ? "received" : "null");

      if (detail) {
        onViewAnalysis(analysisId, detail);
      } else {
        setViewError(analysisId);
      }
    } catch (err) {
      console.error("[History] View error", err);
      setViewError(analysisId);
    } finally {
      setLoadingViewId(null);
    }
  };
  
  const handleDelete = async (analysisId: string) => {
    if (!confirm("Are you sure you want to delete this historical record?")) return;
    const config = getBackendConfig();
    const ok = await deleteHistoryItem(config, analysisId);
    if (ok) {
      loadHistory(true, activeDataset, activeStatus, search);
    }
  };

  // Group by date (Today, Yesterday, Older)
  const groupedHistory = historyItems.reduce((acc, item) => {
    const date = new Date(item.created_at);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    let group = 'Older';
    if (date.toDateString() === today.toDateString()) {
      group = 'TODAY';
    } else if (date.toDateString() === yesterday.toDateString()) {
      group = 'YESTERDAY';
    } else {
      group = date.toLocaleDateString();
    }
    
    if (!acc[group]) acc[group] = [];
    acc[group].push(item);
    return acc;
  }, {} as Record<string, HistorySummary[]>);

  return (
    <div className="w-full max-w-5xl mx-auto px-4 sm:px-12 py-8 sm:py-14 flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-1.5 pb-2">
        <div className="flex items-center gap-2.5">
          <span className="material-symbols-outlined text-primary text-[28px]">history</span>
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-on-surface">
            Query History
          </h1>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="flex flex-col sm:flex-row items-center gap-4 bg-surface-container-low p-4 rounded-2xl border border-outline-variant/30 shadow-sm">
        <form onSubmit={handleSearchSubmit} className="flex-1 w-full relative">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[20px]">search</span>
          <input
            type="text"
            placeholder="Search questions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-surface-container border border-outline-variant/40 rounded-xl py-2 pl-10 pr-4 text-sm text-on-surface focus:border-primary focus:outline-none transition-colors"
          />
        </form>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <select 
            value={activeDataset} 
            onChange={(e) => setActiveDataset(e.target.value)}
            className="flex-1 sm:flex-none bg-surface-container border border-outline-variant/40 rounded-xl py-2 px-3 text-sm text-on-surface focus:border-primary focus:outline-none appearance-none cursor-pointer"
          >
            <option value="all">All Datasets</option>
            {datasets.map(ds => (
              <option key={ds.dataset_id} value={ds.dataset_id}>{ds.dataset_name}</option>
            ))}
          </select>

          <select 
            value={activeStatus} 
            onChange={(e) => setActiveStatus(e.target.value)}
            className="flex-1 sm:flex-none bg-surface-container border border-outline-variant/40 rounded-xl py-2 px-3 text-sm text-on-surface focus:border-primary focus:outline-none appearance-none cursor-pointer"
          >
            <option value="all">All Status</option>
            <option value="success">Successful</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Content */}
      <div className="flex flex-col gap-8">
        {isError && (
          <div className="bg-error/10 border border-error/20 rounded-2xl p-8 flex flex-col items-center justify-center text-center gap-3">
             <span className="material-symbols-outlined text-[32px] text-error">error</span>
             <p className="text-on-surface font-medium">Unable to load query history.</p>
             <button onClick={() => loadHistory(true, activeDataset, activeStatus, search)} className="px-4 py-2 bg-error text-on-error rounded-xl text-sm font-semibold hover:bg-error/90 transition-colors">
               Retry
             </button>
          </div>
        )}

        {/* Skeleton loading state */}
        {isLoading && historyItems.length === 0 && (
          <div className="flex flex-col gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-surface-container-low border border-outline-variant/20 rounded-2xl p-5 shadow-sm animate-pulse">
                <div className="flex flex-col gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-14 h-4 bg-outline-variant/20 rounded-md" />
                    <div className="w-12 h-4 bg-outline-variant/20 rounded-md" />
                    <div className="w-20 h-4 bg-outline-variant/20 rounded-md" />
                  </div>
                  <div className="w-3/4 h-5 bg-outline-variant/20 rounded-md" />
                  <div className="w-1/3 h-3 bg-outline-variant/15 rounded-md" />
                </div>
              </div>
            ))}
          </div>
        )}

        {!isError && historyItems.length === 0 && !isLoading && (
          <div className="bg-surface-container-low border border-outline-variant/20 rounded-2xl p-12 flex flex-col items-center justify-center text-center gap-4 shadow-sm">
             <span className="material-symbols-outlined text-[48px] text-primary/80">history_toggle_off</span>
             <div className="flex flex-col gap-1">
               <h3 className="text-lg font-semibold text-on-surface">No analyses yet</h3>
               <p className="text-sm text-on-surface-variant max-w-md mx-auto">
                 Ask your first question to start building your analysis history.
               </p>
             </div>
             <button 
               onClick={onNavigateHome}
               className="mt-2 px-6 py-2.5 bg-primary text-on-primary rounded-xl text-sm font-semibold hover:shadow-md transition-all flex items-center gap-2"
             >
               <span className="material-symbols-outlined text-[18px]">chat_bubble</span>
               Ask Analyst
             </button>
          </div>
        )}

        {!isError && Object.entries(groupedHistory).map(([group, items]) => (
          <div key={group} className="flex flex-col gap-4">
            <h3 className="text-xs font-bold text-outline uppercase tracking-wider pl-2">{group}</h3>
            <div className="flex flex-col gap-3">
              {items.map((item) => {
                const time = new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                const isFailed = item.status === 'failed';
                const isViewLoading = loadingViewId === item.analysis_id;
                const hasViewError = viewError === item.analysis_id;
                
                return (
                  <motion.div
                    key={item.analysis_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`bg-surface-container-low border ${isFailed ? 'border-error/30' : 'border-outline-variant/20 hover:border-primary/40'} rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row justify-between gap-5 transition-all group`}
                  >
                    <div className="flex flex-col gap-2 flex-1 min-w-0">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        {isFailed ? (
                          <span className="px-2 py-0.5 rounded-md bg-error/10 text-error text-[10px] font-mono font-bold uppercase">
                            Failed
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-md bg-secondary/15 text-secondary text-[10px] font-mono font-bold uppercase">
                            Success
                          </span>
                        )}
                        <span className="text-xs font-mono text-outline">{time}</span>
                        <span className="text-outline text-xs">•</span>
                        <span className="flex items-center gap-1 text-xs text-on-surface-variant">
                          <span className="material-symbols-outlined text-[14px]">dataset</span>
                          {item.dataset_name}
                        </span>
                      </div>
                      
                      <h4 className="text-base font-semibold text-on-surface leading-snug break-words pr-4">
                        "{item.question}"
                      </h4>

                      {isFailed && item.error_message ? (
                        <p className="text-xs text-error/80 mt-1 line-clamp-2">
                          {item.error_message}
                        </p>
                      ) : (
                        <div className="flex items-center gap-3 text-xs font-mono text-outline mt-1">
                          <span>{item.rows_returned} rows</span>
                          <span>•</span>
                          <span>{item.attempts} {item.attempts === 1 ? 'attempt' : 'attempts'}</span>
                          <span>•</span>
                          <span>{(item.execution_time_ms / 1000).toFixed(1)} sec</span>
                        </div>
                      )}

                      {/* View error inline */}
                      {hasViewError && (
                        <p className="text-xs text-error mt-1">
                          Unable to open this analysis. It may have been deleted.
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 sm:self-center shrink-0">
                       <button
                        onClick={() => handleDelete(item.analysis_id)}
                        className="p-2 rounded-xl text-outline hover:text-error hover:bg-error/10 transition-colors"
                        title="Delete record"
                        disabled={!!loadingViewId}
                      >
                        <span className="material-symbols-outlined text-[18px]">delete</span>
                      </button>
                      <button
                        onClick={() => handleView(item.analysis_id)}
                        disabled={!!loadingViewId}
                        className={`px-4 py-2 rounded-xl text-xs font-medium font-mono transition-colors flex items-center gap-1.5 border border-outline-variant/20 ${
                          isViewLoading
                            ? 'bg-primary/10 text-primary cursor-wait'
                            : hasViewError
                              ? 'bg-error/10 text-error hover:bg-error/20'
                              : 'bg-surface-container hover:bg-primary-container text-on-surface hover:text-on-primary-container'
                        }`}
                      >
                        {isViewLoading ? (
                          <>
                            <div className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                            <span>Opening…</span>
                          </>
                        ) : hasViewError ? (
                          <>
                            <span>Retry</span>
                            <span className="material-symbols-outlined text-[14px]">refresh</span>
                          </>
                        ) : (
                          <>
                            <span>View</span>
                            <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                          </>
                        )}
                      </button>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        ))}
        
        {isLoading && historyItems.length > 0 && (
          <div className="flex justify-center p-8">
             <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
          </div>
        )}

        {!isLoading && !isError && historyItems.length > 0 && historyItems.length < totalItems && (
          <div className="flex justify-center pt-4">
            <button
              onClick={() => loadHistory(false)}
              className="px-6 py-2 rounded-full border border-outline-variant/30 text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors text-sm font-medium"
            >
              Load More ({historyItems.length} of {totalItems})
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
