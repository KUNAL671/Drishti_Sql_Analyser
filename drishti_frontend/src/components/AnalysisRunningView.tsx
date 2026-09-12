import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { AiBubble } from './AiBubble';
import { BubbleState } from '../types';

interface AnalysisRunningViewProps {
  userQuery: string;
  onComplete: () => void;
  onErrorTrigger?: () => void;
  targetDataset?: string;
}

const GENERIC_STAGES = [
  "Analyzing dataset context...",
  "Generating SQL query...",
  "Validating syntax and safety bounds...",
  "Executing against database...",
  "Validating results...",
  "Synthesizing business insights..."
];

export const AnalysisRunningView = ({ userQuery, onComplete, targetDataset = 'Active Dataset' }: AnalysisRunningViewProps) => {
  const [currentTextIndex, setCurrentTextIndex] = useState(0);
  const [bubbleState, setBubbleState] = useState<BubbleState>('thinking');

  // Rotate text every 1.5 seconds until the end, then trigger complete
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTextIndex((prev) => {
        if (prev >= GENERIC_STAGES.length - 1) {
          clearInterval(interval);
          setTimeout(() => onComplete(), 500);
          return prev;
        }
        return prev + 1;
      });
    }, 1500);

    return () => clearInterval(interval);
  }, [onComplete]);

  // Update bubble state based on index
  useEffect(() => {
    const states: BubbleState[] = ['thinking', 'scanning', 'generating', 'executing', 'validating', 'verified'];
    setBubbleState(states[Math.min(currentTextIndex, states.length - 1)]);
  }, [currentTextIndex]);

  return (
    <div className="w-full max-w-4xl mx-auto px-8 sm:px-12 py-10 sm:py-14 flex flex-col gap-8 h-[60vh] justify-center items-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center text-center gap-6"
      >
        <div className="relative mb-8">
          {/* Animated rings around the AI Bubble */}
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
            className="absolute inset-[-30px] rounded-full border border-dashed border-primary/30"
          />
          <motion.div
            animate={{ rotate: -360 }}
            transition={{ duration: 12, repeat: Infinity, ease: "linear" }}
            className="absolute inset-[-50px] rounded-full border border-secondary/20"
          />
          <AiBubble state={bubbleState} size="hero" interactive={false} />
        </div>

        <div className="flex flex-col items-center gap-3 mt-4">
          <h2 className="font-headline-sm text-xl text-on-surface font-semibold max-w-2xl truncate">
            "{userQuery}"
          </h2>
          <p className="font-body-sm text-sm text-on-surface-variant flex items-center gap-2">
            Target: <code className="text-primary font-mono bg-primary/10 px-2 py-0.5 rounded">{targetDataset}</code>
          </p>
        </div>

        <div className="h-12 mt-4 relative w-full flex justify-center">
          <AnimatePresence mode="wait">
            <motion.div 
              key={currentTextIndex}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="absolute font-mono text-sm text-secondary bg-secondary/10 px-4 py-2 rounded-full border border-secondary/20 flex items-center gap-2 shadow-sm"
            >
              <span className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
              {GENERIC_STAGES[currentTextIndex]}
            </motion.div>
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
};
