import { useEffect, useRef } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'motion/react';
import { PageId } from '../types';

interface SidebarProps {
  activePage: PageId;
  onSelectPage: (page: PageId) => void;
  activeDatasetName?: string;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const Sidebar = ({
  activePage,
  onSelectPage,
  activeDatasetName = 'India Employment Data (2018-2024)',
  isCollapsed = false,
  onToggleCollapse,
}: SidebarProps) => {
  const eyeRef = useRef<HTMLDivElement>(null);
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const smoothX = useSpring(mouseX, { damping: 20, stiffness: 200, mass: 0.6 });
  const smoothY = useSpring(mouseY, { damping: 20, stiffness: 200, mass: 0.6 });
  const pupilX = useTransform(smoothX, [-1, 1], [-11, 11]);
  const pupilY = useTransform(smoothY, [-1, 1], [-6, 6]);

  useEffect(() => {
    const handlePointerMove = (e: MouseEvent) => {
      if (!eyeRef.current) return;
      const rect = eyeRef.current.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = e.clientX - cx;
      const dy = e.clientY - cy;
      const dist = Math.hypot(dx, dy);

      if (dist < 1) {
        mouseX.set(0);
        mouseY.set(0);
        return;
      }

      const angle = Math.atan2(dy, dx);
      const intensity = Math.min(1.0, (dist / (dist + 120)) * 1.15);
      mouseX.set(Math.cos(angle) * intensity);
      mouseY.set(Math.sin(angle) * intensity);
    };

    const handlePointerLeave = () => {
      mouseX.set(0);
      mouseY.set(0);
    };

    window.addEventListener('mousemove', handlePointerMove, { passive: true });
    document.addEventListener('mouseleave', handlePointerLeave);
    window.addEventListener('blur', handlePointerLeave);

    return () => {
      window.removeEventListener('mousemove', handlePointerMove);
      document.removeEventListener('mouseleave', handlePointerLeave);
      window.removeEventListener('blur', handlePointerLeave);
    };
  }, [mouseX, mouseY]);

  const navItems: { id: PageId; label: string; icon: string }[] = [
    { id: 'new-analysis', label: 'New Analysis', icon: 'auto_awesome' },
    { id: 'workspace-and-analysis', label: 'Workspace & Analysis', icon: 'terminal' },
    { id: 'query-history', label: 'Query History', icon: 'history_toggle_off' },
    { id: 'datasets', label: 'Datasets', icon: 'database' },
    { id: 'schema-explorer', label: 'Schema Explorer', icon: 'account_tree' },
    { id: 'settings', label: 'Settings', icon: 'settings' },
  ];

  return (
    <aside
      className={`fixed left-0 top-0 h-full ${
        isCollapsed ? 'w-20' : 'w-72'
      } transition-all duration-300 ease-in-out bg-surface-container-lowest border-r border-outline-variant/15 z-50 flex flex-col justify-between select-none overflow-hidden`}
    >
      <div className="flex flex-col">
        {/* Brand Header with toggle button */}
        <div
          className={`pt-7 pb-5 ${
            isCollapsed ? 'px-3 flex flex-col items-center gap-3' : 'px-6 flex items-center justify-between'
          }`}
        >
          <div className="flex items-center gap-3">
            {/* Drishti Eye Aperture Symbol (Follows cursor) */}
            <div
              ref={eyeRef}
              className="w-9 h-9 rounded-xl bg-surface-container-high/80 flex items-center justify-center p-1.5 border border-primary/20 shadow-sm overflow-hidden flex-shrink-0"
              title="Drishti Autonomous Engine"
            >
              <svg className="w-full h-full" viewBox="0 0 100 100" fill="none">
                <defs>
                  <clipPath id="sidebarEyeClip">
                    <path d="M 15 50 Q 50 15 85 50 Q 50 85 15 50 Z" />
                  </clipPath>
                </defs>
                {/* Aperture Eyelid Socket */}
                <path
                  d="M 15 50 Q 50 15 85 50 Q 50 85 15 50 Z"
                  fill="rgba(128, 131, 255, 0.15)"
                  stroke="#c0c1ff"
                  strokeWidth="6"
                />
                {/* Eyeball pupil following cursor */}
                <g clipPath="url(#sidebarEyeClip)">
                  <motion.g style={{ x: pupilX, y: pupilY }}>
                    <circle cx="50" cy="50" r="14" fill="#8083ff" />
                    <circle cx="53" cy="47" r="3.5" fill="#ffffff" />
                  </motion.g>
                </g>
              </svg>
            </div>

            {!isCollapsed && (
              <div className="flex flex-col">
                <span className="text-[17px] tracking-tight text-on-surface font-semibold leading-tight">
                  DRISHTI
                </span>
                <span className="text-[10px] text-primary/80 tracking-widest uppercase font-mono mt-0.5">
                  Autonomous SQL
                </span>
              </div>
            )}
          </div>

          {/* Minimize / Expand Toggle Button */}
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className="p-1.5 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
              title={isCollapsed ? 'Expand sidebar' : 'Minimize sidebar'}
            >
              <span className="material-symbols-outlined text-[20px]">
                {isCollapsed ? 'keyboard_double_arrow_right' : 'keyboard_double_arrow_left'}
              </span>
            </button>
          )}
        </div>

        {/* Navigation Items */}
        <div className={isCollapsed ? 'px-2 py-2' : 'px-4 py-2'}>
          <nav className="flex flex-col gap-2">
            {navItems.map((item) => {
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectPage(item.id)}
                  title={isCollapsed ? item.label : undefined}
                  className={`relative flex items-center ${
                    isCollapsed ? 'justify-center p-3' : 'gap-3.5 px-4 py-3'
                  } rounded-xl transition-all text-left group ${
                    isActive
                      ? 'bg-primary/10 text-primary font-medium shadow-[0_0_16px_rgba(128,131,255,0.08)]'
                      : 'text-on-surface-variant hover:bg-surface-container-high/60 hover:text-on-surface'
                  }`}
                >
                  {/* Subtle active indicator */}
                  {isActive && (
                    <motion.span
                      layoutId="activeNavIndicator"
                      className={`absolute ${
                        isCollapsed ? 'left-0.5 top-2 bottom-2 w-1' : 'left-1 top-2.5 bottom-2.5 w-1'
                      } bg-primary rounded-full`}
                      transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                    />
                  )}

                  <span
                    className={`material-symbols-outlined text-[20px] transition-transform duration-200 group-hover:scale-105 ${
                      isActive ? 'text-primary' : 'text-on-surface-variant group-hover:text-on-surface'
                    }`}
                  >
                    {item.icon}
                  </span>
                  {!isCollapsed && (
                    <span className="text-sm font-medium tracking-tight whitespace-nowrap">
                      {item.label}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Sidebar Footer */}
      <div className={`${isCollapsed ? 'p-3 items-center' : 'p-6'} flex flex-col gap-4 border-t border-outline-variant/10`}>
        {!isCollapsed && (
          <div className="flex flex-col gap-1 px-1">
            <span className="text-[10px] text-outline font-mono uppercase tracking-wider">
              Selected Dataset
            </span>
            <span className="text-xs text-on-surface-variant font-medium truncate" title={activeDatasetName}>
              {activeDatasetName}
            </span>
          </div>
        )}

        <div className={`flex items-center ${isCollapsed ? 'justify-center' : 'justify-between'} pt-2 border-t border-outline-variant/10 px-1`}>
          {!isCollapsed && (
            <div className="flex items-center gap-2 text-xs text-outline font-mono">
              <span>SQL Engine v4</span>
            </div>
          )}
          <button
            onClick={() => onSelectPage('settings')}
            className="text-on-surface-variant hover:text-on-surface p-1.5 rounded-lg hover:bg-surface-container transition-colors"
            title="Open Settings"
          >
            <span className="material-symbols-outlined text-[18px]">tune</span>
          </button>
        </div>
      </div>
    </aside>
  );
};
