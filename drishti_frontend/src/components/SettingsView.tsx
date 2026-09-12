import { useState } from 'react';
import {
  getBackendConfig,
  saveBackendConfig,
  checkBackendHealth,
  BackendConfig,
} from '../services/backendApi';

export const SettingsView = () => {
  // Basic UI & Display settings
  const [defaultView, setDefaultView] = useState<string>('new-analysis');
  const [eyeTrackingEnabled, setEyeTrackingEnabled] = useState<boolean>(true);
  const [chartTheme, setChartTheme] = useState<'modern' | 'minimal'>('modern');
  const [defaultRowLimit, setDefaultRowLimit] = useState<number>(25);
  const [autoRunAnalysis, setAutoRunAnalysis] = useState<boolean>(true);

  // Safety & Execution settings
  const [readOnlyLock, setReadOnlyLock] = useState<boolean>(true);
  const [astLinterStrict, setAstLinterStrict] = useState<boolean>(true);
  const [timeoutMs, setTimeoutMs] = useState<number>(1500);
  const [activeDialect, setActiveDialect] = useState<string>('PostgreSQL 15+');

  // Pre-made backend configuration
  const [backendConfig, setBackendConfig] = useState<BackendConfig>(getBackendConfig());
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [resetSuccess, setResetSuccess] = useState(false);

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    const res = await checkBackendHealth(backendConfig.baseUrl);
    setIsTesting(false);
    if (res.ok) {
      setTestResult({
        ok: true,
        msg: `Backend Online: Successfully pinged ${backendConfig.baseUrl} in ${res.latencyMs}ms.`,
      });
    } else {
      setTestResult({
        ok: false,
        msg: `Backend Offline: Could not reach ${backendConfig.baseUrl}. Using local mock pipeline.`,
      });
    }
  };

  const handleSaveBackend = () => {
    saveBackendConfig(backendConfig);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2500);
  };

  const handleResetDefaults = () => {
    const defaultConfig: BackendConfig = {
      baseUrl: 'http://localhost:8000/api',
      apiKey: '',
      useLiveBackend: false,
      timeoutMs: 5000,
    };
    setBackendConfig(defaultConfig);
    saveBackendConfig(defaultConfig);
    setReadOnlyLock(true);
    setAstLinterStrict(true);
    setTimeoutMs(1500);
    setActiveDialect('PostgreSQL 15+');
    setResetSuccess(true);
    setTimeout(() => setResetSuccess(false), 2000);
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-6 py-10 flex flex-col gap-8 pb-24">
      {/* Header */}
      <div className="flex flex-col gap-1 pb-2">
        <div className="flex items-center gap-2.5">
          <span className="material-symbols-outlined text-primary text-[24px]">settings</span>
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-on-surface">
            Settings & Controls
          </h1>
        </div>
        <p className="text-sm text-on-surface-variant font-normal">
          Connect your pre-made backend, adjust display preferences, and configure SQL execution parameters.
        </p>
      </div>

      {/* 1. Pre-made Backend Integration Section */}
      <div className="bg-surface-container-low border border-outline-variant/30 rounded-2xl p-6 sm:p-7 shadow-sm flex flex-col gap-5">
        <div className="flex items-center justify-between border-b border-outline-variant/15 pb-4">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-primary text-[20px]">cloud_sync</span>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-on-surface font-mono">
              Pre-made Working Backend Connection
            </h2>
          </div>
          <span
            className={`text-xs font-mono px-3 py-1 rounded-full font-medium ${
              backendConfig.useLiveBackend
                ? 'bg-secondary/15 text-secondary border border-secondary/30'
                : 'bg-surface-container text-on-surface-variant'
            }`}
          >
            {backendConfig.useLiveBackend ? 'Active Routing' : 'Standalone Frontend'}
          </span>
        </div>

        {/* Live Backend Toggle */}
        <div className="flex items-center justify-between py-2 border-b border-outline-variant/15">
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-semibold text-on-surface">Route to Pre-made Backend</span>
            <span className="text-xs text-on-surface-variant">
              Forward natural language questions and dataset queries directly to your existing backend service.
            </span>
          </div>
          <button
            onClick={() =>
              setBackendConfig((prev) => ({
                ...prev,
                useLiveBackend: !prev.useLiveBackend,
              }))
            }
            className={`w-12 h-6 rounded-full transition-colors relative p-0.5 ${
              backendConfig.useLiveBackend ? 'bg-secondary' : 'bg-surface-container-highest'
            }`}
          >
            <div
              className={`w-5 h-5 rounded-full bg-surface-container-lowest transition-transform ${
                backendConfig.useLiveBackend ? 'translate-x-6' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Base URL */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-mono text-on-surface-variant">Backend API Base URL</label>
          <input
            type="text"
            value={backendConfig.baseUrl}
            onChange={(e) =>
              setBackendConfig((prev) => ({ ...prev, baseUrl: e.target.value }))
            }
            placeholder="e.g. http://localhost:8000/api or https://api.yourdomain.com"
            className="bg-surface-container border border-outline-variant/30 rounded-xl px-4 py-2.5 text-xs font-mono text-on-surface focus:outline-none focus:border-primary"
          />
        </div>

        {/* API Key / Token */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-mono text-on-surface-variant">Authorization Header / Token (Optional)</label>
          <input
            type="password"
            value={backendConfig.apiKey}
            onChange={(e) =>
              setBackendConfig((prev) => ({ ...prev, apiKey: e.target.value }))
            }
            placeholder="Bearer token or API secret key..."
            className="bg-surface-container border border-outline-variant/30 rounded-xl px-4 py-2.5 text-xs font-mono text-on-surface focus:outline-none focus:border-primary"
          />
        </div>

        {/* Test Result Message */}
        {testResult && (
          <div
            className={`text-xs font-mono px-4 py-2.5 rounded-xl border flex items-center gap-2 ${
              testResult.ok
                ? 'bg-secondary/10 border-secondary/30 text-secondary'
                : 'bg-surface-container border-outline-variant/20 text-on-surface-variant'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">
              {testResult.ok ? 'check_circle' : 'info'}
            </span>
            <span>{testResult.msg}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between pt-2">
          <button
            onClick={handleTestConnection}
            disabled={isTesting}
            className="px-4 py-2 rounded-xl bg-surface-container hover:bg-surface-container-high border border-outline-variant/30 text-xs font-medium text-on-surface transition-colors flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-[16px]">sensors</span>
            <span>{isTesting ? 'Connecting...' : 'Test Backend Connection'}</span>
          </button>

          <button
            onClick={handleSaveBackend}
            className="px-5 py-2 rounded-xl bg-primary text-on-primary text-xs font-semibold hover:brightness-110 transition-all flex items-center gap-1.5 shadow-sm"
          >
            <span>{saveSuccess ? 'Saved!' : 'Save Backend Configuration'}</span>
            {saveSuccess && <span className="material-symbols-outlined text-[14px]">check</span>}
          </button>
        </div>
      </div>

      {/* 2. Basic Interface & Experience Preferences */}
      <div className="bg-surface-container-low border border-outline-variant/30 rounded-2xl p-6 sm:p-7 shadow-sm flex flex-col gap-5">
        <div className="flex items-center gap-2.5 border-b border-outline-variant/15 pb-4">
          <span className="material-symbols-outlined text-primary text-[20px]">tune</span>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-on-surface font-mono">
            Interface & Display Preferences
          </h2>
        </div>

        {/* Living Eye Tracking Toggle */}
        <div className="flex items-center justify-between py-2 border-b border-outline-variant/15">
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-semibold text-on-surface">Living Eye Cursor Tracking</span>
            <span className="text-xs text-on-surface-variant">
              Follows cursor position with iris & pupil depth calculation.
            </span>
          </div>
          <button
            onClick={() => setEyeTrackingEnabled(!eyeTrackingEnabled)}
            className={`w-12 h-6 rounded-full transition-colors relative p-0.5 ${
              eyeTrackingEnabled ? 'bg-primary' : 'bg-surface-container-highest'
            }`}
          >
            <div
              className={`w-5 h-5 rounded-full bg-surface-container-lowest transition-transform ${
                eyeTrackingEnabled ? 'translate-x-6' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Auto Run Pipeline */}
        <div className="flex items-center justify-between py-2 border-b border-outline-variant/15">
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-semibold text-on-surface">Auto-Execute Analysis Pipeline</span>
            <span className="text-xs text-on-surface-variant">
              Immediately proceeds through AST verification and SQL sandbox upon submission.
            </span>
          </div>
          <button
            onClick={() => setAutoRunAnalysis(!autoRunAnalysis)}
            className={`w-12 h-6 rounded-full transition-colors relative p-0.5 ${
              autoRunAnalysis ? 'bg-primary' : 'bg-surface-container-highest'
            }`}
          >
            <div
              className={`w-5 h-5 rounded-full bg-surface-container-lowest transition-transform ${
                autoRunAnalysis ? 'translate-x-6' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Default Row Limit */}
        <div className="flex items-center justify-between py-2 border-b border-outline-variant/15">
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-semibold text-on-surface">Default Query Record Limit</span>
            <span className="text-xs text-on-surface-variant">
              Maximum rows returned by generated analytical queries.
            </span>
          </div>
          <select
            value={defaultRowLimit}
            onChange={(e) => setDefaultRowLimit(Number(e.target.value))}
            className="bg-surface-container border border-outline-variant/30 rounded-xl px-3 py-1.5 text-xs font-mono text-on-surface focus:outline-none"
          >
            <option value={10}>10 records</option>
            <option value={25}>25 records (recommended)</option>
            <option value={50}>50 records</option>
            <option value={100}>100 records</option>
          </select>
        </div>

        {/* Default SQL Dialect */}
        <div className="flex items-center justify-between py-2">
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-semibold text-on-surface">Target SQL Engine Dialect</span>
            <span className="text-xs text-on-surface-variant">
              Syntax dialect for generated CTEs and window functions.
            </span>
          </div>
          <select
            value={activeDialect}
            onChange={(e) => setActiveDialect(e.target.value)}
            className="bg-surface-container border border-outline-variant/30 rounded-xl px-3 py-1.5 text-xs font-mono text-on-surface focus:outline-none"
          >
            <option>PostgreSQL 15+</option>
            <option>DuckDB / MotherDuck</option>
            <option>Google BigQuery</option>
            <option>Snowflake Standard</option>
          </select>
        </div>
      </div>

      {/* 3. Safety & Transaction Boundaries */}
      <div className="bg-surface-container-low border border-outline-variant/30 rounded-2xl p-6 sm:p-7 shadow-sm flex flex-col gap-5">
        <div className="flex items-center gap-2.5 border-b border-outline-variant/15 pb-4">
          <span className="material-symbols-outlined text-primary text-[20px]">shield</span>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-on-surface font-mono">
            Safety & Sandbox Boundaries
          </h2>
        </div>

        {/* Read-only toggle */}
        <div className="flex items-center justify-between py-2 border-b border-outline-variant/15">
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-semibold text-on-surface">Enforce Read-Only Isolation</span>
            <span className="text-xs text-on-surface-variant">
              Blocks UPDATE, DELETE, DROP, or ALTER commands from being processed.
            </span>
          </div>
          <button
            onClick={() => setReadOnlyLock(!readOnlyLock)}
            className={`w-12 h-6 rounded-full transition-colors relative p-0.5 ${
              readOnlyLock ? 'bg-secondary' : 'bg-surface-container-highest'
            }`}
          >
            <div
              className={`w-5 h-5 rounded-full bg-surface-container-lowest transition-transform ${
                readOnlyLock ? 'translate-x-6' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Timeout Slider */}
        <div className="flex flex-col gap-2 py-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-on-surface">Execution Timeout Guard</span>
            <span className="text-xs font-mono text-secondary font-bold">{timeoutMs} ms</span>
          </div>
          <input
            type="range"
            min={500}
            max={5000}
            step={250}
            value={timeoutMs}
            onChange={(e) => setTimeoutMs(Number(e.target.value))}
            className="w-full accent-primary cursor-pointer"
          />
        </div>
      </div>

      {/* Reset to Defaults */}
      <div className="flex items-center justify-between pt-2">
        <span className="text-xs text-on-surface-variant">
          Need to restore original default settings?
        </span>
        <button
          onClick={handleResetDefaults}
          className="px-4 py-2 rounded-xl bg-surface-container hover:bg-surface-container-high border border-outline-variant/30 text-xs font-medium text-on-surface transition-colors flex items-center gap-1.5"
        >
          <span>{resetSuccess ? 'Restored ✓' : 'Reset to Defaults'}</span>
        </button>
      </div>
    </div>
  );
};
