import { useState, useEffect, useRef, useId } from 'react';
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  AnimatePresence,
} from 'motion/react';
import { BubbleState } from '../types';

interface AiBubbleProps {
  state?: BubbleState;
  size?: 'hero' | 'compact' | 'mini';
  className?: string;
  badgeLabel?: string;
  onClick?: () => void;
  interactive?: boolean;
}

export const AiBubble = ({
  state = 'idle',
  size = 'hero',
  className = '',
  badgeLabel,
  onClick,
  interactive = true,
}: AiBubbleProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const uniqueId = useId().replace(/:/g, '');

  // Dimension configurations
  const dimMap = {
    hero: {
      wrapperSize: 140, // px
      ringSize: 160,
      glowSpread: 'w-64 h-64',
      badge: '-bottom-3 text-xs',
      pupilRadius: 18,
      shadowSize: 'w-28 h-6',
      eyeScale: 1,
    },
    compact: {
      wrapperSize: 96,
      ringSize: 112,
      glowSpread: 'w-44 h-44',
      badge: '-bottom-2 text-[10px]',
      pupilRadius: 13,
      shadowSize: 'w-20 h-4',
      eyeScale: 0.72,
    },
    mini: {
      wrapperSize: 44,
      ringSize: 52,
      glowSpread: 'w-24 h-24',
      badge: 'hidden',
      pupilRadius: 6,
      shadowSize: 'w-10 h-2',
      eyeScale: 0.35,
    },
  };

  const currentDim = dimMap[size];

  // -------------------------------------------------------------
  // -------------------------------------------------------------
  // 3D Interactive Tilt & Gaze Physics Engine
  // -------------------------------------------------------------
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  // Responsive spring configuration for fluid, organic ocular saccades
  const springConfig = { damping: 20, stiffness: 220, mass: 0.6 };
  const smoothX = useSpring(mouseX, springConfig);
  const smoothY = useSpring(mouseY, springConfig);

  // Map mouse offsets (-1 to 1) to degrees of 3D tilt for the outer orb
  const tiltMax = size === 'hero' ? 22 : size === 'compact' ? 14 : 8;
  const rotateX = useTransform(smoothY, [-1, 1], [tiltMax, -tiltMax]);
  const rotateY = useTransform(smoothX, [-1, 1], [-tiltMax, tiltMax]);

  // Eyeball & Pupil gaze shifts inside the aperture (in SVG viewBox units)
  const pupilMaxX = size === 'hero' ? 18 : size === 'compact' ? 13 : 7;
  const pupilMaxY = size === 'hero' ? 10 : size === 'compact' ? 7 : 4;
  const pupilShiftX = useTransform(smoothX, [-1, 1], [-pupilMaxX, pupilMaxX]);
  const pupilShiftY = useTransform(smoothY, [-1, 1], [-pupilMaxY, pupilMaxY]);

  // Aperture socket subtle parallax shift
  const apertureParallaxX = useTransform(smoothX, [-1, 1], [-5, 5]);
  const apertureParallaxY = useTransform(smoothY, [-1, 1], [-3.5, 3.5]);

  // Parallax reflection shift for glass cornea highlight
  const specularShiftX = useTransform(smoothX, [-1, 1], [12, -12]);
  const specularShiftY = useTransform(smoothY, [-1, 1], [10, -10]);

  // Ground shadow offset opposite to tilt
  const shadowX = useTransform(smoothX, [-1, 1], [-14, 14]);
  const shadowScale = useTransform(smoothY, [-1, 1], [0.92, 1.08]);

  const [isHovered, setIsHovered] = useState(false);

  // Global cursor tracker so the eye tracks the cursor anywhere across the entire window
  useEffect(() => {
    if (!interactive) return;

    const handlePointerMove = (e: MouseEvent | TouchEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      let clientX = 0;
      let clientY = 0;

      if ('touches' in e && e.touches.length > 0) {
        clientX = e.touches[0].clientX;
        clientY = e.touches[0].clientY;
      } else if ('clientX' in e) {
        clientX = (e as MouseEvent).clientX;
        clientY = (e as MouseEvent).clientY;
      }

      const deltaX = clientX - centerX;
      const deltaY = clientY - centerY;
      const distance = Math.hypot(deltaX, deltaY);

      if (distance < 1) {
        mouseX.set(0);
        mouseY.set(0);
        return;
      }

      // Smooth gaze calculation:
      // Distance saturation curve: intensity smoothly approaches 1.0 as cursor moves away
      // but scales smoothly from 0 at center so nearby cursor movements are gentle and precise.
      const angle = Math.atan2(deltaY, deltaX);
      const intensity = Math.min(1.0, (distance / (distance + 120)) * 1.15);

      const targetX = Math.cos(angle) * intensity;
      const targetY = Math.sin(angle) * intensity;

      mouseX.set(targetX);
      mouseY.set(targetY);
    };

    const handlePointerLeave = () => {
      mouseX.set(0);
      mouseY.set(0);
      setIsHovered(false);
    };

    window.addEventListener('mousemove', handlePointerMove, { passive: true });
    window.addEventListener('touchmove', handlePointerMove, { passive: true });
    document.addEventListener('mouseleave', handlePointerLeave);
    window.addEventListener('blur', handlePointerLeave);

    return () => {
      window.removeEventListener('mousemove', handlePointerMove);
      window.removeEventListener('touchmove', handlePointerMove);
      document.removeEventListener('mouseleave', handlePointerLeave);
      window.removeEventListener('blur', handlePointerLeave);
    };
  }, [interactive, mouseX, mouseY]);

  // -------------------------------------------------------------
  // State-Driven 3D Dynamics & Color Accents
  // -------------------------------------------------------------
  // Ambient Glow Palettes
  const glowGradients: Record<BubbleState, string> = {
    idle: 'from-[#8083ff]/35 via-[#ddb7ff]/25 to-[#4edea3]/30',
    thinking: 'from-[#8083ff]/55 via-[#b76dff]/45 to-[#c0c1ff]/40',
    scanning: 'from-[#4edea3]/55 via-[#8083ff]/45 to-[#ddb7ff]/40',
    generating: 'from-[#b76dff]/60 via-[#8083ff]/50 to-[#4edea3]/40',
    validating: 'from-[#8083ff]/65 via-[#4edea3]/55 to-[#6ffbbe]/50',
    executing: 'from-[#4edea3]/70 via-[#8083ff]/60 to-[#6ffbbe]/60',
    verified: 'from-[#4edea3]/60 via-[#6ffbbe]/45 to-[#8083ff]/30',
    error: 'from-[#ffb4ab]/60 via-[#93000a]/50 to-[#34343a]',
    'follow-up': 'from-[#8083ff]/55 via-[#ddb7ff]/35 to-[#4edea3]/45',
  };

  // Outer 3D Gyro Ring Speeds
  const ringDuration =
    state === 'executing'
      ? 5
      : state === 'generating' || state === 'scanning'
      ? 9
      : state === 'thinking'
      ? 14
      : 22;

  // Primary accent colors for light glows & satellites
  const accentColor =
    state === 'verified'
      ? '#4edea3'
      : state === 'error'
      ? '#ffb4ab'
      : state === 'executing'
      ? '#6ffbbe'
      : '#c0c1ff';

  return (
    <div
      ref={containerRef}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{ perspective: 1200 }}
      className={`relative flex flex-col items-center justify-center select-none ${
        interactive ? 'cursor-pointer' : ''
      } ${className}`}
    >
      {/* 1. Volumetric 3D Ambient Aura Background */}
      <motion.div
        animate={{
          scale: state === 'executing' ? [1.1, 1.25, 1.1] : [1, 1.12, 1],
          opacity: state === 'executing' ? [0.65, 0.9, 0.65] : [0.45, 0.7, 0.45],
        }}
        transition={{
          duration: state === 'executing' ? 1.6 : 3.8,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        className={`absolute ${currentDim.glowSpread} bg-gradient-to-r ${glowGradients[state]} rounded-full blur-3xl pointer-events-none -z-10`}
      />

      {/* 2. Primary 3D Transform Anchor Container */}
      <motion.div
        style={{
          rotateX,
          rotateY,
          transformStyle: 'preserve-3d',
        }}
        animate={{
          y: state === 'executing' ? [-8, 8, -8] : [-5, 5, -5],
        }}
        transition={{
          y: {
            duration: state === 'executing' ? 2 : 4.5,
            repeat: Infinity,
            ease: 'easeInOut',
          },
        }}
        whileHover={interactive ? { scale: 1.05 } : undefined}
        whileTap={interactive ? { scale: 0.94, z: -20 } : undefined}
        className="relative flex items-center justify-center"
      >
        {/* ========================================================= */}
        {/* 3D GYROSCOPE RING 1 (Pitch 68deg, continuous Z spin)     */}
        {/* ========================================================= */}
        <div
          style={{
            width: currentDim.ringSize,
            height: currentDim.ringSize,
            transformStyle: 'preserve-3d',
            transform: 'rotateX(68deg) rotateY(12deg)',
          }}
          className="absolute pointer-events-none flex items-center justify-center"
        >
          <motion.div
            animate={{ rotateZ: 360 }}
            transition={{ duration: ringDuration, repeat: Infinity, ease: 'linear' }}
            className="w-full h-full rounded-full border border-[#8083ff]/30 border-dashed relative flex items-center justify-center"
            style={{
              boxShadow: '0 0 12px rgba(128, 131, 255, 0.2)',
            }}
          >
            {/* Glowing Orbital Satellite Node */}
            <div
              style={{
                transform: 'translateZ(6px)',
                backgroundColor: accentColor,
                boxShadow: `0 0 10px ${accentColor}`,
              }}
              className="absolute top-0 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full"
            />
          </motion.div>
        </div>

        {/* ========================================================= */}
        {/* 3D GYROSCOPE RING 2 (Yaw 68deg, Roll 30deg, reverse spin)*/}
        {/* ========================================================= */}
        <div
          style={{
            width: currentDim.ringSize * 0.92,
            height: currentDim.ringSize * 0.92,
            transformStyle: 'preserve-3d',
            transform: 'rotateY(68deg) rotateX(25deg)',
          }}
          className="absolute pointer-events-none flex items-center justify-center"
        >
          <motion.div
            animate={{ rotateZ: -360 }}
            transition={{ duration: ringDuration * 1.35, repeat: Infinity, ease: 'linear' }}
            className="w-full h-full rounded-full border border-[#4edea3]/35 relative flex items-center justify-center"
            style={{
              boxShadow: '0 0 10px rgba(78, 222, 163, 0.2)',
            }}
          >
            {/* Secondary Satellite Node */}
            <div
              style={{
                transform: 'translateZ(4px)',
                backgroundColor: state === 'verified' ? '#4edea3' : '#ddb7ff',
                boxShadow: `0 0 8px ${state === 'verified' ? '#4edea3' : '#ddb7ff'}`,
              }}
              className="absolute bottom-0 right-1/4 w-1.5 h-1.5 rounded-full"
            />
          </motion.div>
        </div>

        {/* ========================================================= */}
        {/* 3D EQUATORIAL CELESTIAL RING                             */}
        {/* ========================================================= */}
        <div
          style={{
            width: currentDim.ringSize * 0.85,
            height: currentDim.ringSize * 0.85,
            transformStyle: 'preserve-3d',
            transform: 'rotateX(20deg) rotateZ(15deg)',
          }}
          className="absolute pointer-events-none flex items-center justify-center"
        >
          <motion.div
            animate={{ rotateZ: 360 }}
            transition={{ duration: ringDuration * 1.8, repeat: Infinity, ease: 'linear' }}
            className="w-full h-full rounded-full border border-white/10 relative"
          >
            <div className="absolute top-1/2 left-0 -translate-y-1/2 w-1 h-1 rounded-full bg-white/60 shadow-[0_0_6px_#fff]" />
            <div className="absolute top-1/2 right-0 -translate-y-1/2 w-1 h-1 rounded-full bg-white/60 shadow-[0_0_6px_#fff]" />
          </motion.div>
        </div>

        {/* ========================================================= */}
        {/* VOLUMETRIC 3D GLASS SPHERE (Core Orb Body)                */}
        {/* ========================================================= */}
        <div
          style={{
            width: currentDim.wrapperSize,
            height: currentDim.wrapperSize,
            transformStyle: 'preserve-3d',
            transform: 'translateZ(0px)',
          }}
          className="relative rounded-full flex items-center justify-center shadow-[0_20px_50px_rgba(0,0,0,0.85)] border border-white/15 overflow-visible"
        >
          {/* Deep Spherical Volumetric Shading Layer */}
          <div
            style={{
              background:
                state === 'verified'
                  ? 'radial-gradient(circle at 35% 30%, #0d3824 0%, #061c12 55%, #020b07 100%)'
                  : state === 'error'
                  ? 'radial-gradient(circle at 35% 30%, #4a0d10 0%, #200406 55%, #0c0203 100%)'
                  : 'radial-gradient(circle at 35% 30%, #1e1b38 0%, #111020 50%, #090812 100%)',
              boxShadow: `
                inset 0 0 24px rgba(255, 255, 255, 0.15),
                inset -6px -6px 20px rgba(0, 0, 0, 0.9),
                inset 8px 8px 18px ${accentColor}25,
                0 0 25px ${accentColor}30
              `,
            }}
            className="absolute inset-0 rounded-full"
          />

          {/* Internal Volumetric Core Glow / Corona */}
          <motion.div
            animate={{
              scale: state === 'executing' ? [0.85, 1.05, 0.85] : [0.92, 1, 0.92],
              opacity: [0.6, 0.9, 0.6],
            }}
            transition={{
              duration: state === 'executing' ? 1.4 : 3,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
            style={{
              transform: 'translateZ(8px)',
              background: `radial-gradient(circle, ${accentColor}45 0%, transparent 70%)`,
            }}
            className="absolute inset-2 rounded-full pointer-events-none"
          />

          {/* ======================================================= */}
          {/* SUSPENDED 3D CYBERNETIC APERTURE / IRIS                 */}
          {/* ======================================================= */}
          <motion.div
            style={{
              transform: 'translateZ(18px)',
              x: apertureParallaxX,
              y: apertureParallaxY,
            }}
            className="relative z-10 w-full h-full flex items-center justify-center p-3 pointer-events-none"
          >
            <svg
              className="w-full h-full"
              viewBox="0 0 120 120"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <linearGradient
                  id={`eyeGrad-${uniqueId}`}
                  x1="15"
                  y1="15"
                  x2="105"
                  y2="105"
                  gradientUnits="userSpaceOnUse"
                >
                  <stop stopColor={state === 'error' ? '#ffb4ab' : '#c0c1ff'} />
                  <stop offset="0.5" stopColor={state === 'verified' ? '#4edea3' : '#ddb7ff'} />
                  <stop offset="1" stopColor={state === 'verified' ? '#6ffbbe' : '#8083ff'} />
                </linearGradient>

                <radialGradient
                  id={`pupilDepthGrad-${uniqueId}`}
                  cx="0"
                  cy="0"
                  r="1"
                  gradientUnits="userSpaceOnUse"
                  gradientTransform="translate(60 60) scale(20)"
                >
                  <stop stopColor={state === 'verified' ? '#003824' : '#2b2745'} />
                  <stop offset="0.75" stopColor="#0d0e14" />
                  <stop offset="1" stopColor="#000000" />
                </radialGradient>

                <radialGradient
                  id={`irisGlowGrad-${uniqueId}`}
                  cx="60"
                  cy="60"
                  r="26"
                  gradientUnits="userSpaceOnUse"
                >
                  <stop stopColor={accentColor} stopOpacity="0.55" />
                  <stop offset="0.6" stopColor={accentColor} stopOpacity="0.2" />
                  <stop offset="1" stopColor="transparent" />
                </radialGradient>

                <clipPath id={`eyeClip-${uniqueId}`}>
                  <path d="M 18 60 Q 60 18 102 60 Q 60 102 18 60 Z" />
                </clipPath>
              </defs>

              {/* Concentric Cybernetic Compass Grid */}
              <circle
                cx="60"
                cy="60"
                r="46"
                stroke="currentColor"
                className="text-white/10"
                strokeDasharray="2 6"
                strokeWidth="1"
              />
              <circle
                cx="60"
                cy="60"
                r="36"
                stroke={accentColor}
                strokeOpacity="0.3"
                strokeWidth="1"
              />

              {/* Aperture Eye Outline (Socket / Sclera) */}
              <path
                d="M 18 60 Q 60 18 102 60 Q 60 102 18 60 Z"
                fill="rgba(8, 9, 15, 0.75)"
                stroke={`url(#eyeGrad-${uniqueId})`}
                strokeWidth={size === 'hero' ? 2.5 : 2}
                className="drop-shadow-[0_0_8px_rgba(128,131,255,0.4)]"
              />

              {/* =================================================== */}
              {/* DYNAMIC EYEBALL: Follows cursor, clipped to eyelids */}
              {/* =================================================== */}
              <g clipPath={`url(#eyeClip-${uniqueId})`}>
                <motion.g
                  style={{
                    x: pupilShiftX,
                    y: pupilShiftY,
                  }}
                >
                  {/* Iris Volumetric Aura */}
                  <circle
                    cx="60"
                    cy="60"
                    r={currentDim.pupilRadius + 8}
                    fill={`url(#irisGlowGrad-${uniqueId})`}
                  />

                  {/* Iris Cybernetic Reticle Ring */}
                  <circle
                    cx="60"
                    cy="60"
                    r={currentDim.pupilRadius + 3}
                    stroke={accentColor}
                    strokeOpacity="0.45"
                    strokeWidth="1.2"
                    strokeDasharray="2 3"
                    fill="none"
                  />

                  {/* Central Dynamic Pupil */}
                  <motion.circle
                    cx="60"
                    cy="60"
                    animate={{
                      r:
                        state === 'executing'
                          ? currentDim.pupilRadius * 1.15
                          : state === 'thinking'
                          ? currentDim.pupilRadius * 0.88
                          : currentDim.pupilRadius,
                    }}
                    transition={{ duration: 0.6, ease: 'easeOut' }}
                    fill={`url(#pupilDepthGrad-${uniqueId})`}
                    stroke={accentColor}
                    strokeWidth="1.4"
                    strokeOpacity="0.75"
                  />

                  {/* Specular Inner Glints (naturally follow the pupil) */}
                  <circle cx="64" cy="55" r="3.2" fill="#ffffff" opacity="0.95" />
                  <circle
                    cx="67"
                    cy="52"
                    r="1.7"
                    fill={state === 'verified' ? '#6ffbbe' : '#c0c1ff'}
                    opacity="0.9"
                  />
                </motion.g>
              </g>

              {/* Scanning / Validating Laser sweep */}
              {(state === 'scanning' || state === 'validating') && (
                <motion.line
                  x1="36"
                  x2="84"
                  y1="40"
                  y2="40"
                  stroke="#4edea3"
                  strokeWidth="2"
                  animate={{ y1: [38, 82, 38], y2: [38, 82, 38] }}
                  transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
                  className="drop-shadow-[0_0_8px_#4edea3]"
                />
              )}
            </svg>
          </motion.div>

          {/* ======================================================= */}
          {/* 3D PARALLAX SPECULAR HIGHLIGHT (Glass Lens Top Layer)   */}
          {/* ======================================================= */}
          <motion.div
            style={{
              transform: 'translateZ(28px)',
              x: specularShiftX,
              y: specularShiftY,
            }}
            className="absolute top-2 left-4 w-1/3 h-1/4 rounded-full bg-gradient-to-b from-white/40 via-white/10 to-transparent pointer-events-none blur-[0.5px] rotate-[-25deg]"
          />

          {/* Bottom Rim Light Highlight */}
          <div
            style={{ transform: 'translateZ(15px)' }}
            className="absolute bottom-1 right-3 w-1/4 h-1/5 rounded-full bg-gradient-to-t from-white/15 to-transparent pointer-events-none blur-[1px] rotate-[15deg]"
          />
        </div>

        {/* Dynamic State Status Badge (3D Floating in front) */}
        {size !== 'mini' && (
          <motion.div
            style={{
              transform: 'translateZ(34px)',
            }}
            className={`absolute ${currentDim.badge} bg-surface-container-high/90 backdrop-blur-md px-2.5 py-0.5 rounded-full shadow-xl flex items-center gap-1.5 border border-white/10 whitespace-nowrap z-30 pointer-events-none`}
          >
            <span
              style={{ backgroundColor: accentColor }}
              className={`w-1.5 h-1.5 rounded-full ${
                state === 'verified'
                  ? 'shadow-[0_0_8px_#4edea3]'
                  : state === 'error'
                  ? 'shadow-[0_0_8px_#ffb4ab]'
                  : 'shadow-[0_0_6px_#c0c1ff] animate-ping'
              }`}
            />
            <span className="font-mono text-[10px] text-on-surface uppercase tracking-wider font-semibold">
              {badgeLabel ||
                (state === 'verified'
                  ? 'Verified AST'
                  : state === 'thinking'
                  ? 'Reasoning...'
                  : state === 'validating'
                  ? 'Validating...'
                  : state === 'executing'
                  ? 'Executing Sandbox'
                  : 'DRISHTI')}
            </span>
          </motion.div>
        )}
      </motion.div>

      {/* ========================================================= */}
      {/* 3D GROUND SHADOW (Reactions with depth & tilt)            */}
      {/* ========================================================= */}
      <motion.div
        style={{
          x: shadowX,
          scaleX: shadowScale,
        }}
        animate={{
          scale: state === 'executing' ? [0.95, 1.08, 0.95] : [0.9, 1.02, 0.9],
          opacity: state === 'executing' ? [0.55, 0.35, 0.55] : [0.4, 0.25, 0.4],
        }}
        transition={{
          duration: state === 'executing' ? 2 : 4.5,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        className={`mt-4 ${currentDim.shadowSize} bg-black/60 rounded-full blur-md pointer-events-none -z-20`}
      />
    </div>
  );
};
