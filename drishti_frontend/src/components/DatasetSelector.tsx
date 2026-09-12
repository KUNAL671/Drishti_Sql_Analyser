import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { DatasetItem } from '../types';

interface DatasetSelectorProps {
  currentDataset: string;
  datasets: DatasetItem[];
  onSelectDataset: (name: string) => void;
  onUploadNew?: () => void;
  compact?: boolean;
  direction?: 'up' | 'down' | 'auto';
}

export const DatasetSelector = ({
  currentDataset,
  datasets,
  onSelectDataset,
  onUploadNew,
  compact = false,
  direction = 'auto',
}: DatasetSelectorProps) => {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [searchFilter, setSearchFilter] = useState<string>('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Determine dropdown placement class based on direction prop
  const placementClass =
    direction === 'up'
      ? 'bottom-full mb-2 left-0'
      : direction === 'down'
      ? 'top-full mt-2 left-0'
      : 'top-full mt-2 left-0';

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const filteredDatasets = datasets.filter(
    (d) =>
      d.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
      d.tablePath.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const selectedItem = datasets.find((d) => d.title === currentDataset) || datasets[0];

  return (
    <div className="relative inline-block" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className={`group flex items-center gap-2 rounded-xl transition-all border ${
          isOpen
            ? 'bg-surface-container-high border-primary/50 text-on-surface ring-2 ring-primary/15'
            : 'bg-surface-container/80 hover:bg-surface-container-high border-outline-variant/30 text-on-surface-variant hover:text-on-surface'
        } ${compact ? 'px-2.5 py-1 text-xs' : 'px-3 py-1.5 text-xs'}`}
        title="Click to switch dataset for this analysis"
      >
        <span className="material-symbols-outlined text-[16px] text-primary group-hover:scale-110 transition-transform">
          database
        </span>

        <span className="font-mono font-medium truncate max-w-[200px] sm:max-w-[260px] text-left">
          {selectedItem?.title || currentDataset}
        </span>

        <span
          className={`material-symbols-outlined text-[16px] text-outline transition-transform duration-200 ${
            isOpen ? 'rotate-180 text-primary' : ''
          }`}
        >
          keyboard_arrow_down
        </span>
      </button>

      {/* Floating Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.98 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className={`absolute ${placementClass} w-80 sm:w-96 bg-surface-container-low/98 backdrop-blur-xl border border-outline-variant/40 rounded-2xl shadow-2xl p-3 z-50 flex flex-col gap-2.5`}
          >
            {/* Header & Search */}
            <div className="flex items-center justify-between pb-1 border-b border-outline-variant/20 px-1">
              <span className="text-xs font-semibold text-on-surface uppercase font-mono tracking-wider">
                Select Target Dataset
              </span>
              <span className="text-[10px] font-mono text-outline">
                {datasets.length} available
              </span>
            </div>

            {/* Quick Search */}
            <div className="flex items-center gap-2 bg-surface-container rounded-xl px-3 py-1.5 border border-outline-variant/20 text-xs">
              <span className="material-symbols-outlined text-[15px] text-outline">search</span>
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Filter datasets or table paths..."
                className="bg-transparent text-on-surface placeholder:text-outline w-full focus:outline-none text-xs"
                autoFocus
              />
              {searchFilter && (
                <button
                  type="button"
                  onClick={() => setSearchFilter('')}
                  className="text-outline hover:text-on-surface"
                >
                  <span className="material-symbols-outlined text-[14px]">close</span>
                </button>
              )}
            </div>

            {/* Dataset List */}
            <div className="max-h-56 overflow-y-auto flex flex-col gap-1 pr-0.5 custom-scrollbar">
              {filteredDatasets.length > 0 ? (
                filteredDatasets.map((d) => {
                  const isSelected = d.title === currentDataset;

                  return (
                    <button
                      key={d.id}
                      type="button"
                      onClick={() => {
                        onSelectDataset(d.title);
                        setIsOpen(false);
                      }}
                      className={`w-full text-left p-2.5 rounded-xl transition-all flex items-start justify-between gap-2.5 ${
                        isSelected
                          ? 'bg-primary/15 border border-primary/30 text-on-surface'
                          : 'hover:bg-surface-container text-on-surface-variant hover:text-on-surface border border-transparent'
                      }`}
                    >
                      <div className="flex flex-col min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-xs text-on-surface truncate">
                            {d.title}
                          </span>
                          {isSelected && (
                            <span className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-primary text-on-primary font-bold">
                              ACTIVE
                            </span>
                          )}
                        </div>
                        <span className="text-[11px] font-mono text-outline truncate mt-0.5">
                          {d.tablePath}
                        </span>
                        <div className="flex items-center gap-2 text-[10px] font-mono text-outline mt-1">
                          <span>{d.type}</span>
                          <span>•</span>
                          <span>{d.rows}</span>
                        </div>
                      </div>

                      <div className="flex items-center self-center flex-shrink-0">
                        <span
                          className={`material-symbols-outlined text-[18px] ${
                            isSelected ? 'text-primary' : 'text-outline/40'
                          }`}
                        >
                          {isSelected ? 'check_circle' : 'radio_button_unchecked'}
                        </span>
                      </div>
                    </button>
                  );
                })
              ) : (
                <div className="text-center py-4 text-xs text-outline font-mono">
                  No datasets match "{searchFilter}"
                </div>
              )}
            </div>

            {/* Footer Action: Add/Upload new dataset */}
            {onUploadNew && (
              <div className="pt-2 border-t border-outline-variant/20 flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => {
                    setIsOpen(false);
                    onUploadNew();
                  }}
                  className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-xl bg-surface-container hover:bg-surface-container-high border border-outline-variant/30 text-xs font-medium text-primary hover:text-primary transition-colors"
                >
                  <span className="material-symbols-outlined text-[15px]">upload_file</span>
                  <span>Upload / Connect New Dataset</span>
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
