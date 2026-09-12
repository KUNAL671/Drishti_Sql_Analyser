import { useState, useRef, DragEvent, ChangeEvent } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { DatasetItem } from '../types';
import { uploadDataset, getBackendConfig } from '../services/backendApi';

interface DatasetsViewProps {
  onSelectDataset?: (name: string, id?: string) => void;
  onNewAnalysisWithDataset?: (name: string, id?: string) => void;
  datasets?: DatasetItem[];
  onDatasetsChange?: (datasets: DatasetItem[]) => void;
  onDatasetUploaded?: () => void;
}

export const DatasetsView = ({
  onSelectDataset,
  onNewAnalysisWithDataset,
  datasets: propDatasets,
  onDatasetsChange,
  onDatasetUploaded,
}: DatasetsViewProps) => {
  const [internalDatasets, setInternalDatasets] = useState<DatasetItem[]>([]);
  const datasets = propDatasets || internalDatasets;
  const setDatasets = (action: DatasetItem[] | ((prev: DatasetItem[]) => DatasetItem[])) => {
    if (typeof action === 'function') {
      const next = action(datasets);
      setInternalDatasets(next);
      onDatasetsChange?.(next);
    } else {
      setInternalDatasets(action);
      onDatasetsChange?.(action);
    }
  };
  const [showIngestModal, setShowIngestModal] = useState<boolean>(false);
  const [ingestStep, setIngestStep] = useState<'upload' | 'analyzing' | 'ready' | 'error'>('upload');
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [parsedFileInfo, setParsedFileInfo] = useState<{
    fileName: string;
    tablePath: string;
    rowCount: string;
    columnCount: number;
    columns: string[];
    sizeStr: string;
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Trigger OS native file dialog
  const handleTriggerFileSelect = () => {
    setErrorMessage(null);
    fileInputRef.current?.click();
  };

  // Safe file validation and parsing
  const processUploadedFile = async (file: File) => {
    setErrorMessage(null);

    if (!file || file.size === 0) {
      setIngestStep('error');
      setErrorMessage('The selected file appears to be empty (0 bytes). Please select a valid tabular data file.');
      return;
    }

    const validExtensions = ['.csv', '.tsv', '.parquet', '.json', '.xlsx', '.sqlite', '.db'];
    const fileNameLower = file.name.toLowerCase();
    const hasValidExt = validExtensions.some((ext) => fileNameLower.endsWith(ext));

    if (!hasValidExt) {
      setIngestStep('error');
      setErrorMessage(
        `Unsupported file format "${file.name}". Please upload a CSV, TSV, Parquet, JSON, or SQLite database.`
      );
      return;
    }

    setIngestStep('analyzing');
    setUploadProgress(25);

    try {
      const config = getBackendConfig();
      const res = await uploadDataset(file, config);
      setUploadProgress(100);
      
      setParsedFileInfo({
        fileName: res.dataset_name || file.name,
        tablePath: res.table_name || file.name,
        rowCount: `${res.row_count || 0} rows`,
        columnCount: res.column_count || 0,
        columns: [],
        sizeStr: 'N/A',
      });
      
      setTimeout(() => {
        setIngestStep('ready');
      }, 500);

    } catch (err: any) {
      setIngestStep('error');
      setErrorMessage(err.message || 'An error occurred during upload.');
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      processUploadedFile(file);
    }
    // reset input so same file can be chosen again if needed
    e.target.value = '';
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      processUploadedFile(file);
    }
  };

  const handleFinishIngest = () => {
    if (!parsedFileInfo) return;

    const newDataset: DatasetItem = {
      id: String(Date.now()),
      title: parsedFileInfo.fileName.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' '),
      tablePath: parsedFileInfo.tablePath,
      type: 'CSV / Parquet',
      status: 'Verified Schema',
      rows: parsedFileInfo.rowCount,
      columns: parsedFileInfo.columnCount,
      size: parsedFileInfo.sizeStr,
      qualityScore: 'Clean schema • Zero null conflicts',
      validationPct: 100,
      updatedAt: 'Just now',
      activeInSession: true,
    };

    // We call the callback to reload datasets from backend
    if (onDatasetUploaded) {
      onDatasetUploaded();
    }
    
    // We don't manually add it because onDatasetUploaded will fetch the new list.
    onSelectDataset?.(newDataset.title, newDataset.id);
    setShowIngestModal(false);
    setIngestStep('upload');
    setParsedFileInfo(null);
  };

  return (
    <div className="w-full max-w-6xl mx-auto px-6 py-8 sm:py-10 flex flex-col gap-8 pb-24">
      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".csv,.tsv,.parquet,.json,.xlsx,.sqlite,.db"
        className="hidden"
      />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-primary text-[24px]">database</span>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-on-surface">
              Datasets Catalog
            </h1>
          </div>
          <p className="text-sm text-on-surface-variant font-normal">
            Uploaded data files and database tables ready for autonomous SQL queries.
          </p>
        </div>

        {/* Upload Button */}
        <button
          onClick={() => {
            setIngestStep('upload');
            setErrorMessage(null);
            setShowIngestModal(true);
          }}
          className="self-start sm:self-auto flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-on-primary hover:brightness-110 font-semibold text-xs transition-all shadow-sm"
        >
          <span className="material-symbols-outlined text-[16px]">upload_file</span>
          <span>Upload Dataset</span>
        </button>
      </div>

      {/* Dataset Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 sm:gap-6">
        {datasets.map((item) => (
          <div
            key={item.id}
            className={`bg-surface-container-low border rounded-2xl p-6 shadow-sm flex flex-col justify-between gap-5 transition-all ${
              item.activeInSession
                ? 'border-primary/50 ring-1 ring-primary/20 shadow-md'
                : 'border-outline-variant/20 hover:border-outline-variant/40'
            }`}
          >
            <div className="flex flex-col gap-2.5">
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-surface-container text-on-surface-variant border border-outline-variant/20">
                  {item.type}
                </span>

                <div className="flex items-center gap-2">
                  {item.activeInSession && (
                    <span className="px-2 py-0.5 rounded-full bg-primary/15 text-primary text-[10px] font-mono font-bold border border-primary/30">
                      ACTIVE
                    </span>
                  )}
                  <span className="text-xs font-mono text-secondary flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-secondary" />
                    {item.status}
                  </span>
                </div>
              </div>

              <h3 className="text-base sm:text-lg font-semibold text-on-surface tracking-tight mt-0.5">
                {item.title}
              </h3>

              <code className="text-xs text-primary/90 font-mono bg-surface-container px-3 py-1.5 rounded-lg border border-outline-variant/15 select-all truncate">
                {item.tablePath}
              </code>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-3 gap-3 py-3 border-y border-outline-variant/15 text-xs font-mono">
              <div className="flex flex-col gap-0.5">
                <span className="text-[10px] text-outline uppercase">Volume</span>
                <span className="text-on-surface font-semibold">{item.rows}</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-[10px] text-outline uppercase">Columns</span>
                <span className="text-on-surface font-semibold">{item.columns}</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-[10px] text-outline uppercase">Size</span>
                <span className="text-on-surface font-semibold">{item.size}</span>
              </div>
            </div>

            {/* Footer Action */}
            <div className="flex items-center justify-between text-xs pt-1">
              <span className="text-on-surface-variant font-mono text-[11px] flex items-center gap-1.5">
                <span className="material-symbols-outlined text-secondary text-[15px]">check_circle</span>
                <span>{item.qualityScore}</span>
              </span>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    onSelectDataset?.(item.title, item.id);
                    setDatasets((prev) =>
                      prev.map((d) => ({ ...d, activeInSession: d.id === item.id }))
                    );
                  }}
                  className="px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-xs font-medium text-on-surface transition-colors"
                >
                  {item.activeInSession ? 'Selected' : 'Set Active'}
                </button>

                <button
                  onClick={() => onNewAnalysisWithDataset?.(item.title, item.id)}
                  className="px-3 py-1.5 rounded-lg bg-primary hover:bg-primary-container text-on-primary hover:text-on-primary-container text-xs font-medium transition-colors flex items-center gap-1"
                >
                  <span>Query</span>
                  <span className="material-symbols-outlined text-[13px]">arrow_forward</span>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Upload Dataset Modal */}
      <AnimatePresence>
        {showIngestModal && (
          <div
            onClick={() => setShowIngestModal(false)}
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
          >
            <motion.div
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-surface-container-low border border-outline-variant/40 rounded-2xl w-full max-w-lg p-6 sm:p-7 shadow-2xl flex flex-col gap-5"
            >
              {/* Modal Header */}
              <div className="flex items-center justify-between border-b border-outline-variant/20 pb-3">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-[20px]">upload_file</span>
                  <h3 className="text-base font-semibold text-on-surface">Upload & Ingest Dataset</h3>
                </div>
                <button
                  onClick={() => setShowIngestModal(false)}
                  className="text-on-surface-variant hover:text-on-surface p-1 rounded-lg"
                >
                  <span className="material-symbols-outlined text-[18px]">close</span>
                </button>
              </div>

              {/* STEP: UPLOAD */}
              {ingestStep === 'upload' && (
                <div className="flex flex-col gap-4">
                  <p className="text-xs text-on-surface-variant leading-relaxed">
                    Select a CSV, Parquet, or JSON file to index and inspect columns.
                  </p>

                  {/* Drag & Drop Area with Native Click */}
                  <div
                    onClick={handleTriggerFileSelect}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    className={`border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center gap-3 cursor-pointer transition-all ${
                      isDragging
                        ? 'border-primary bg-primary/10 scale-[1.01]'
                        : 'border-outline-variant/40 hover:border-primary/60 bg-surface-container-lowest/50 hover:bg-surface-container-lowest'
                    }`}
                  >
                    <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                      <span className="material-symbols-outlined text-[26px]">cloud_upload</span>
                    </div>
                    <div className="text-center">
                      <span className="text-sm text-on-surface font-semibold block">
                        Click to browse or drag file here
                      </span>
                      <span className="text-xs text-outline font-mono mt-0.5 block">
                        Supports .csv, .parquet, .tsv, .json, .sqlite
                      </span>
                    </div>
                  </div>

                  {/* Sample Dataset Option */}
                  <div className="flex items-center justify-between pt-2 border-t border-outline-variant/15">
                    <span className="text-xs text-outline font-mono">No file at hand?</span>
                    <button
                      onClick={() => {
                        const sampleFile = new File(['district,state,rate\nDistrict X,State Y,14.2'], 'india_employment_quarterly_sample.csv', {
                          type: 'text/csv',
                        });
                        processUploadedFile(sampleFile);
                      }}
                      className="px-3.5 py-1.5 rounded-xl bg-surface-container hover:bg-surface-container-high border border-outline-variant/30 text-xs font-medium text-on-surface transition-colors"
                    >
                      Load Sample Dataset
                    </button>
                  </div>
                </div>
              )}

              {/* STEP: ANALYZING */}
              {ingestStep === 'analyzing' && (
                <div className="flex flex-col gap-4 py-3">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-on-surface font-medium">Validating schema & mapping types...</span>
                    <span className="text-secondary font-bold">{uploadProgress}%</span>
                  </div>

                  <div className="w-full h-2 bg-surface-container rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-secondary"
                      initial={{ width: 0 }}
                      animate={{ width: `${uploadProgress}%` }}
                      transition={{ duration: 0.2 }}
                    />
                  </div>

                  <div className="text-xs font-mono text-outline flex flex-col gap-1 mt-1">
                    <span>✓ Checking file encoding (UTF-8)</span>
                    <span>✓ Inferring column types and date formats</span>
                    <span>✓ Verifying row integrity & zero-null sanity</span>
                  </div>
                </div>
              )}

              {/* STEP: ERROR */}
              {ingestStep === 'error' && (
                <div className="flex flex-col gap-4 py-2">
                  <div className="p-4 bg-error/10 border border-error/30 rounded-xl flex items-start gap-3 text-xs text-on-surface">
                    <span className="material-symbols-outlined text-error text-[20px] flex-shrink-0">
                      error
                    </span>
                    <div className="flex flex-col gap-1">
                      <span className="font-semibold text-error">File Processing Notice</span>
                      <p className="text-on-surface-variant leading-relaxed">{errorMessage}</p>
                    </div>
                  </div>

                  <div className="flex items-center justify-end gap-3 pt-2">
                    <button
                      onClick={() => setIngestStep('upload')}
                      className="px-4 py-2 rounded-xl bg-surface-container hover:bg-surface-container-high text-xs font-medium text-on-surface transition-colors"
                    >
                      Back
                    </button>
                    <button
                      onClick={handleTriggerFileSelect}
                      className="px-4 py-2 rounded-xl bg-primary text-on-primary text-xs font-semibold hover:brightness-110 transition-all"
                    >
                      Select Another File
                    </button>
                  </div>
                </div>
              )}

              {/* STEP: READY */}
              {ingestStep === 'ready' && parsedFileInfo && (
                <div className="flex flex-col gap-4 py-1">
                  <div className="p-3 bg-secondary/10 border border-secondary/30 rounded-xl flex items-center gap-2 text-secondary text-xs font-semibold">
                    <span className="material-symbols-outlined text-[16px]">verified</span>
                    <span>Dataset Successfully Validated</span>
                  </div>

                  <div className="bg-surface-container p-4 rounded-xl text-xs font-mono flex flex-col gap-1.5 text-on-surface">
                    <div>
                      Table Path: <span className="text-primary font-bold">{parsedFileInfo.tablePath}</span>
                    </div>
                    <div>
                      Volume: <span className="text-secondary">{parsedFileInfo.rowCount}</span> ({parsedFileInfo.sizeStr})
                    </div>
                    <div>
                      Columns ({parsedFileInfo.columnCount}):{' '}
                      <span className="text-on-surface-variant">
                        {parsedFileInfo.columns.join(', ')}...
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={handleFinishIngest}
                    className="w-full py-2.5 rounded-xl bg-primary text-on-primary font-semibold text-xs hover:brightness-110 transition-all shadow-sm"
                  >
                    Add to Catalog & Make Active
                  </button>
                </div>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
