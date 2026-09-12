import { useState, useEffect, type KeyboardEvent } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { AiBubble } from './AiBubble';
import { BubbleState, DatasetItem } from '../types';

import {
  getBackendConfig,
  saveBackendConfig,
  checkBackendHealth,
  BackendConfig,
} from '../services/backendApi';

interface NewAnalysisViewProps {
  onStartAnalysis: (query: string) => void;
  activeDatasetName?: string;
  onSelectDataset?: (name: string) => void;
  availableDatasets?: DatasetItem[];
  onUploadNewDataset?: () => void;
  onNavigateToSchema?: () => void;
}

export const NewAnalysisView = ({
  onStartAnalysis,
  activeDatasetName = 'India Employment Data (2018-2024)',
  onSelectDataset,
  availableDatasets = [],
  onUploadNewDataset,
  onNavigateToSchema,
}: NewAnalysisViewProps) => {
  const [queryText, setQueryText] = useState('');
  const [bubbleState, setBubbleState] = useState<BubbleState>('idle');
  const [isActivating, setIsActivating] = useState(false);
  const [hasEntered, setHasEntered] = useState(false);

  // Pre-made backend connection configuration
  const [backendConfig, setBackendConfig] = useState<BackendConfig>(getBackendConfig());
  const [showBackendModal, setShowBackendModal] = useState(false);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);
  const [healthStatus, setHealthStatus] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setHasEntered(true), 120);
    return () => clearTimeout(timer);
  }, []);

  const handleSubmit = (overrideQuery?: string) => {
    const finalQuery = (overrideQuery || queryText).trim();
    if (!finalQuery) return;

    setIsActivating(true);
    setBubbleState('thinking');

    setTimeout(() => {
      onStartAnalysis(finalQuery);
    }, 450);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleTestBackend = async () => {
    setIsCheckingHealth(true);
    setHealthStatus(null);
    const result = await checkBackendHealth(backendConfig.baseUrl);
    setIsCheckingHealth(false);
    if (result.ok) {
      setHealthStatus(`Online (${result.latencyMs}ms)`);
    } else {
      setHealthStatus('Unreachable (using local sandbox)');
    }
  };

  const handleSaveBackend = () => {
    saveBackendConfig(backendConfig);
    setShowBackendModal(false);
  };

  return (
    <div className="relative w-full max-w-4xl mx-auto px-6 py-12 flex flex-col items-center justify-center min-h-[calc(100vh-6rem)]">
      {/* Subtle atmospheric ambient glow */}
      <div className="absolute top-1/4 w-[500px] h-[500px] bg-primary/5 rounded-full blur-3xl pointer-events-none -z-10" />

      {/* 1. Centered Living AI Bubble with generous breathing space */}
      <motion.div
        initial={{ y: 30, opacity: 0, scale: 0.95 }}
        animate={
          isActivating
            ? { scale: 1.08, y: -4, opacity: 1 }
            : hasEntered
            ? { y: 0, opacity: 1, scale: 1 }
            : { y: 30, opacity: 0, scale: 0.95 }
        }
        transition={{
          type: 'spring',
          stiffness: 240,
          damping: 24,
        }}
        className="mb-8 relative"
      >
        <AiBubble
          state={bubbleState}
          size="hero"
          badgeLabel={isActivating ? 'Connecting Pipeline...' : 'DRISHTI'}
          onClick={() => {
            const states: BubbleState[] = ['idle', 'thinking', 'scanning', 'generating', 'validating', 'executing', 'verified'];
            setBubbleState((prev) => states[(states.indexOf(prev) + 1) % states.length]);
          }}
        />

        <AnimatePresence>
          {isActivating && (
            <motion.div
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1.25 }}
              exit={{ opacity: 0, scale: 1.4 }}
              className="absolute -inset-4 rounded-full border border-primary/30 animate-ping pointer-events-none"
            />
          )}
        </AnimatePresence>
      </motion.div>

      {/* 2. Crisp, Clean Headline with open typography */}
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.5 }}
        className="text-center max-w-xl flex flex-col items-center gap-2 mb-8"
      >
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-on-surface">
          What would you like to analyze?
        </h1>
        <p className="text-base text-on-surface-variant font-medium tracking-wide">
          See The Story In Your Data
        </p>
      </motion.div>

      {/* 3. Spacious, Focused Input Card */}
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25, duration: 0.5 }}
        className="w-full bg-surface-container-low/95 backdrop-blur-xl border border-outline-variant/30 rounded-2xl shadow-xl p-5 sm:p-6 flex flex-col gap-4 relative transition-all duration-200 focus-within:border-primary/60 focus-within:ring-2 focus-within:ring-primary/15"
      >
        <textarea
          value={queryText}
          onChange={(e) => setQueryText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about your data..."
          rows={3}
          className="w-full bg-transparent text-on-surface placeholder:text-outline/70 text-base p-1 focus:outline-none resize-none leading-relaxed"
          autoFocus
        />

        {/* Clean bottom toolbar */}
        <div className="flex items-center justify-between gap-4 pt-3 border-t border-outline-variant/15">
          {/* Keyboard tip */}
          <div className="flex items-center gap-2 text-xs font-mono text-outline">
            <span className="inline-flex items-center gap-1 text-[11px]">
              <span className="px-1.5 py-0.5 rounded bg-surface-container border border-outline-variant/30 text-[10px]">Enter ↵</span>
              <span>to run query</span>
            </span>
            <span className="hidden sm:inline">•</span>
            <span className="hidden sm:inline-flex items-center gap-1 text-[11px]">
              <span className="px-1.5 py-0.5 rounded bg-surface-container border border-outline-variant/30 text-[10px]">Shift + Enter</span>
              <span>new line</span>
            </span>
          </div>

          {/* Submit Action */}
          <div className="flex items-center gap-3">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => handleSubmit()}
              disabled={isActivating || !queryText.trim()}
              className="flex items-center gap-2 px-5 py-2 rounded-xl bg-primary text-on-primary font-semibold text-xs hover:brightness-110 transition-all shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <span>{isActivating ? 'Running...' : 'Analyze'}</span>
              <span className="material-symbols-outlined text-[16px]">arrow_upward</span>
            </motion.button>
          </div>
        </div>
      </motion.div>

      {/* Removed static recommendation chips */}

      {/* 5. Pre-made Backend Connection Modal */}
      <AnimatePresence>
        {showBackendModal && (
          <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="w-full max-w-lg bg-surface-container-low border border-outline-variant/30 rounded-2xl p-6 shadow-2xl flex flex-col gap-4"
            >
              <div className="flex items-center justify-between pb-2 border-b border-outline-variant/20">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-[20px]">
                    cloud_sync
                  </span>
                  <h3 className="text-base font-semibold text-on-surface">
                    Connect Pre-made Backend
                  </h3>
                </div>
                <button
                  onClick={() => setShowBackendModal(false)}
                  className="p-1 text-outline hover:text-on-surface rounded-lg"
                >
                  <span className="material-symbols-outlined text-[18px]">close</span>
                </button>
              </div>

              <p className="text-xs text-on-surface-variant leading-relaxed">
                Connect your existing Python / Node.js backend server. DRISHTI will dispatch queries to
                your API and render SQL, AST verification, and synthesized results.
              </p>

              {/* Mode Toggle */}
              <div className="flex items-center justify-between p-3 rounded-xl bg-surface-container border border-outline-variant/15">
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-on-surface">
                    Live Backend Mode
                  </span>
                  <span className="text-[11px] text-on-surface-variant">
                    {backendConfig.useLiveBackend
                      ? 'Forwarding queries directly to your pre-made backend'
                      : 'Using local verification sandbox replica'}
                  </span>
                </div>
                <button
                  onClick={() =>
                    setBackendConfig((prev) => ({
                      ...prev,
                      useLiveBackend: !prev.useLiveBackend,
                    }))
                  }
                  className={`w-11 h-6 rounded-full transition-colors relative p-0.5 ${
                    backendConfig.useLiveBackend
                      ? 'bg-secondary'
                      : 'bg-surface-container-highest'
                  }`}
                >
                  <div
                    className={`w-5 h-5 rounded-full bg-surface-container-lowest transition-transform ${
                      backendConfig.useLiveBackend ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              {/* Base URL */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-mono text-on-surface-variant">
                  Backend Base URL
                </label>
                <input
                  type="text"
                  value={backendConfig.baseUrl}
                  onChange={(e) =>
                    setBackendConfig((prev) => ({ ...prev, baseUrl: e.target.value }))
                  }
                  placeholder="e.g. http://localhost:8000/api"
                  className="w-full bg-surface-container text-on-surface text-xs font-mono px-3 py-2 rounded-lg border border-outline-variant/30 focus:outline-none focus:border-primary"
                />
              </div>

              {/* API Key (Optional) */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-mono text-on-surface-variant">
                  Authorization Header / API Key (Optional)
                </label>
                <input
                  type="password"
                  value={backendConfig.apiKey}
                  onChange={(e) =>
                    setBackendConfig((prev) => ({ ...prev, apiKey: e.target.value }))
                  }
                  placeholder="Bearer token or secret key..."
                  className="w-full bg-surface-container text-on-surface text-xs font-mono px-3 py-2 rounded-lg border border-outline-variant/30 focus:outline-none focus:border-primary"
                />
              </div>

              {/* Health check feedback */}
              {healthStatus && (
                <div className="text-xs font-mono px-3 py-1.5 rounded-lg bg-surface-container text-on-surface flex items-center justify-between">
                  <span>Server Status:</span>
                  <span className="font-semibold text-secondary">{healthStatus}</span>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center justify-between pt-2">
                <button
                  onClick={handleTestBackend}
                  disabled={isCheckingHealth}
                  className="px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high border border-outline-variant/20 text-xs font-mono text-on-surface-variant hover:text-on-surface transition-colors flex items-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-[14px]">sensors</span>
                  <span>{isCheckingHealth ? 'Pinging...' : 'Test Connection'}</span>
                </button>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowBackendModal(false)}
                    className="px-3 py-1.5 text-xs text-on-surface-variant hover:text-on-surface"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveBackend}
                    className="px-4 py-1.5 rounded-lg bg-primary-container hover:bg-primary text-on-primary-container font-semibold text-xs transition-colors"
                  >
                    Save & Apply
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
