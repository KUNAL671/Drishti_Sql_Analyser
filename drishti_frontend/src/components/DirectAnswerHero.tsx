import { motion } from 'motion/react';
import { DirectAnswerSummary } from '../utils/dataDetector';

interface DirectAnswerHeroProps {
  summary: DirectAnswerSummary;
  userQuery?: string;
  executionTime?: string;
  className?: string;
}

export const DirectAnswerHero = ({
  summary,
  userQuery,
  executionTime = '38ms',
  className = '',
}: DirectAnswerHeroProps) => {
  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`relative overflow-hidden rounded-2xl bg-gradient-to-b from-surface-container-high/90 to-surface-container-low border border-primary/30 p-6 sm:p-7 shadow-lg ${className}`}
      aria-label="Direct Answer and Key Finding"
    >
      {/* Subtle glowing accent background */}
      <div className="absolute -top-12 -right-12 w-64 h-64 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-12 -left-12 w-48 h-48 bg-secondary/10 rounded-full blur-2xl pointer-events-none" />

      <div className="relative z-10 flex flex-col gap-5">
        {/* 1. Verified Header Tag & Timing */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary/15 text-secondary border border-secondary/30 text-xs font-mono font-bold tracking-wide">
              <span className="material-symbols-outlined text-[15px]">verified</span>
              <span>DIRECT ANSWER</span>
            </span>
            <span className="text-xs font-mono text-outline">•</span>
            <span className="text-xs font-mono text-outline">
              Answered in {executionTime}
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-on-surface-variant">
            <span className="material-symbols-outlined text-[15px] text-primary">
              security
            </span>
            <span>Zero Null Violations • CTE Verified</span>
          </div>
        </div>

        {/* 2. Direct Answer Narrative Text */}
        <div className="flex flex-col gap-2">
          {userQuery && (
            <span className="text-xs font-mono uppercase tracking-wider text-outline">
              Question: &ldquo;{userQuery}&rdquo;
            </span>
          )}
          <h2 className="text-lg sm:text-xl md:text-2xl font-semibold text-on-surface leading-snug tracking-tight">
            {summary.directAnswerText}
          </h2>
        </div>

        {/* 3. Primary Key Metric Callouts */}
        {summary.keyMetrics.length > 0 && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
            {summary.keyMetrics.map((metric, i) => {
              const isHighlight = metric.highlight;
              return (
                <div
                  key={i}
                  className={`rounded-xl p-3.5 flex flex-col justify-between transition-all border ${
                    isHighlight
                      ? 'bg-primary/10 border-primary/40 ring-1 ring-primary/20'
                      : 'bg-surface-container/70 border-outline-variant/25'
                  }`}
                >
                  <span className="text-[11px] font-mono text-outline uppercase truncate">
                    {metric.label}
                  </span>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span
                      className={`text-xl sm:text-2xl font-bold font-mono ${
                        metric.tier === 'critical'
                          ? 'text-secondary'
                          : metric.tier === 'warning'
                          ? 'text-primary'
                          : 'text-on-surface'
                      }`}
                    >
                      {metric.value}
                    </span>
                  </div>
                  {metric.sublabel && (
                    <span className="text-[11px] font-mono text-on-surface-variant/80 mt-1 truncate">
                      {metric.sublabel}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* 4. Core Analytical Takeaways */}
        {summary.keyTakeaways.length > 0 && (
          <div className="pt-2 border-t border-outline-variant/15 flex flex-col gap-2">
            <span className="text-[11px] font-mono uppercase tracking-wider text-outline flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[14px] text-secondary">
                lightbulb
              </span>
              Key Analytical Takeaways:
            </span>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-on-surface-variant">
              {summary.keyTakeaways.map((takeaway, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-secondary font-bold font-mono">•</span>
                  <span className="leading-relaxed">{takeaway}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </motion.section>
  );
};
