import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { RECOMMENDED_QUERIES } from '../data/mockData';

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectQuery: (query: string) => void;
}

export const SearchModal = ({ isOpen, onClose, onSelectQuery }: SearchModalProps) => {
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!isOpen) return null;

  const matches = RECOMMENDED_QUERIES.filter(
    (q) =>
      q.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      q.tables.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center pt-24 p-4"
    >
      <motion.div
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, y: -20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -20, scale: 0.95 }}
        className="w-full max-w-2xl bg-surface-container-low border border-outline-variant/40 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
      >
        {/* Search Bar Input */}
        <div className="p-4 border-b border-outline-variant/20 flex items-center gap-3 bg-surface-container-lowest">
          <span className="material-symbols-outlined text-[20px] text-primary">search</span>
          <input
            autoFocus
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search queries, schemas, table columns, or actions..."
            className="flex-1 bg-transparent text-on-surface text-sm placeholder:text-outline focus:outline-none"
          />
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-outline hover:text-on-surface hover:bg-surface-container transition-colors"
            title="Close Search"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        {/* Results List */}
        <div className="p-space-sm max-h-80 overflow-y-auto flex flex-col gap-1">
          <span className="text-[10px] font-mono text-outline uppercase px-2 py-1">
            Suggested Prompts & Schemas
          </span>

          {matches.map((item, idx) => (
            <div
              key={idx}
              onClick={() => {
                onSelectQuery(item.title);
                onClose();
              }}
              className="p-space-sm hover:bg-surface-container rounded-lg cursor-pointer flex items-center justify-between transition-colors group"
            >
              <div className="flex items-center gap-space-sm">
                <span className="material-symbols-outlined text-[16px] text-primary">auto_awesome</span>
                <span className="text-xs text-on-surface group-hover:text-primary transition-colors">
                  {item.title}
                </span>
              </div>
              <span className="text-[10px] font-mono text-outline">{item.tables}</span>
            </div>
          ))}

          {matches.length === 0 && (
            <div className="p-space-md text-center text-xs text-outline font-mono">
              No matching queries found. Type to trigger dynamic search.
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};
