import { motion } from 'motion/react';
import { PageId } from '../types';

interface HeaderProps {
  activePage: PageId;
  onNewQuestion: () => void;
  onOpenSearch: () => void;
  activeDatasetName?: string;
  currentQuery?: string;
  isSidebarCollapsed?: boolean;
}

export const Header = ({
  activePage,
  onNewQuestion,
  onOpenSearch,
  activeDatasetName = 'India Employment Data (2018-2024)',
  currentQuery,
  isSidebarCollapsed = false,
}: HeaderProps) => {
  // Determine header context title based on query made or active dataset
  const displayTitle =
    activePage === 'workspace-and-analysis' && currentQuery
      ? currentQuery
      : activeDatasetName;

  const isQueryDisplay = activePage === 'workspace-and-analysis' && Boolean(currentQuery);

  return (
    <header
      className={`fixed top-0 ${
        isSidebarCollapsed ? 'left-20' : 'left-72'
      } right-0 h-16 bg-surface/85 backdrop-blur-xl border-b border-outline-variant/20 z-40 flex items-center justify-between px-6 transition-all duration-300 ease-in-out`}
    >
      {/* Left: Active Dataset or Query Title (Static clean label, no button) */}
      <div className="flex items-center gap-3 min-w-0 pr-4">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="material-symbols-outlined text-[17px] text-primary flex-shrink-0">
            {isQueryDisplay ? 'terminal' : 'analytics'}
          </span>
          <div className="flex flex-col min-w-0">
            <span className="text-[10px] uppercase font-mono tracking-wider text-outline leading-tight">
              {isQueryDisplay ? 'Active Query' : 'Active Dataset'}
            </span>
            <span
              className="text-sm font-semibold text-on-surface truncate max-w-xs sm:max-w-sm md:max-w-md lg:max-w-xl"
              title={displayTitle}
            >
              {displayTitle}
            </span>
          </div>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-3 flex-shrink-0">
        {/* Search Schemas / SQL trigger (No shortcut kbd) */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onOpenSearch}
          className="hidden sm:flex items-center gap-2 bg-surface-container-low hover:bg-surface-container border border-outline-variant/30 px-3 py-1.5 rounded-lg text-on-surface-variant hover:text-on-surface transition-all shadow-sm group text-xs"
        >
          <span className="material-symbols-outlined text-[15px] group-hover:text-primary transition-colors">
            search
          </span>
          <span className="font-normal">Search schemas & SQL...</span>
        </motion.button>

        {/* New Question Action Button - Adjusted to fit neatly */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.96 }}
          onClick={onNewQuestion}
          className="flex items-center gap-1.5 bg-primary-container hover:bg-primary text-on-primary-container hover:text-on-primary px-3.5 py-1.5 rounded-lg transition-colors text-xs font-semibold shadow-sm whitespace-nowrap"
        >
          <span className="material-symbols-outlined text-[16px]">add</span>
          <span>New Question</span>
        </motion.button>
      </div>
    </header>
  );
};
