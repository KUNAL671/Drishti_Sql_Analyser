import { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  ComposedChart,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from 'recharts';
import {
  analyzeAndDetectVisualization,
  DetectedChartType,
  MetricDefinition,
} from '../utils/dataDetector';

interface AutoDataVisualizerProps {
  data: Record<string, any>[];
  queryPrompt?: string;
  title?: string;
  subtitle?: string;
  className?: string;
}

const PALETTE = [
  '#4edea3', // Vibrant emerald (secondary)
  '#8083ff', // Clean indigo (primary-container)
  '#ddb7ff', // Soft lavender (tertiary)
  '#ffb4ab', // Coral alert (error)
  '#38bdf8', // Sky blue
  '#facc15', // Amber
  '#fb7185', // Rose
];

export const AutoDataVisualizer = ({
  data,
  queryPrompt,
  title,
  subtitle,
  className = '',
}: AutoDataVisualizerProps) => {
  // 1. Run detection engine
  const detection = useMemo(
    () => analyzeAndDetectVisualization(data, queryPrompt),
    [data, queryPrompt]
  );

  const [selectedChartType, setSelectedChartType] = useState<DetectedChartType>(
    detection.recommendedChart
  );
  const [selectedMetricKey, setSelectedMetricKey] = useState<string>(
    detection.primaryMetric.key
  );
  const [showReasoning, setShowReasoning] = useState<boolean>(false);
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc' | 'original'>('desc');

  // Update selection if underlying recommended chart changes (e.g. follow-up query with different shape)
  useEffect(() => {
    setSelectedChartType(detection.recommendedChart);
    setSelectedMetricKey(detection.primaryMetric.key);
  }, [detection.recommendedChart, detection.primaryMetric.key]);

  // Active metric configuration
  const activeMetric: MetricDefinition =
    detection.availableMetrics.find((m) => m.key === selectedMetricKey) ||
    detection.primaryMetric;

  // Prepared chart data with sorting
  const chartData = useMemo(() => {
    const list = data.map((item, idx) => {
      const catLabel =
        item[detection.categoryKey] ||
        item.district ||
        item.state ||
        item.year ||
        item.name ||
        `Item ${idx + 1}`;
      return {
        ...item,
        __displayName: String(catLabel),
      };
    });

    if (sortOrder === 'original' || detection.temporalKey) {
      return list;
    }

    return list.sort((a, b) => {
      const valA = Number(a[activeMetric.key]) || 0;
      const valB = Number(b[activeMetric.key]) || 0;
      return sortOrder === 'desc' ? valB - valA : valA - valB;
    });
  }, [data, detection.categoryKey, detection.temporalKey, activeMetric.key, sortOrder]);

  // Average metric for reference line
  const avgValue = useMemo(() => {
    if (!chartData.length) return 0;
    const sum = chartData.reduce(
      (acc, cur) => acc + (Number(cur[activeMetric.key]) || 0),
      0
    );
    return sum / chartData.length;
  }, [chartData, activeMetric.key]);

  // Chart icon helper
  const getChartIcon = (type: DetectedChartType) => {
    switch (type) {
      case 'ranked-bar':
        return 'bar_chart';
      case 'grouped-bar':
        return 'grouped_bar_chart';
      case 'time-series':
        return 'show_chart';
      case 'donut':
        return 'donut_large';
      case 'composed':
        return 'stacked_line_chart';
      case 'kpi-card':
        return 'pin';
      default:
        return 'analytics';
    }
  };

  const getChartLabel = (type: DetectedChartType) => {
    switch (type) {
      case 'ranked-bar':
        return 'Ranked Bar';
      case 'grouped-bar':
        return 'Comparison Bars';
      case 'time-series':
        return 'Trend Area';
      case 'donut':
        return 'Distribution Donut';
      case 'composed':
        return 'Dual-Axis Composed';
      case 'kpi-card':
        return 'Key Metric';
      default:
        return 'Chart';
    }
  };

  // Custom Dark Tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;

    return (
      <div className="bg-surface-container-high/95 backdrop-blur-md border border-outline-variant/40 rounded-xl p-3 shadow-2xl text-xs flex flex-col gap-1.5 min-w-[180px]">
        <span className="font-semibold text-on-surface border-b border-outline-variant/20 pb-1">
          {label || payload[0]?.payload?.__displayName}
        </span>
        {payload.map((entry: any, i: number) => {
          const val = Number(entry.value);
          const isRate =
            entry.name?.toLowerCase().includes('rate') ||
            entry.name?.toLowerCase().includes('surge') ||
            entry.name?.toLowerCase().includes('delta');
          const formatted = isRate
            ? `${val >= 0 && entry.name?.toLowerCase().includes('surge') ? '+' : ''}${val.toFixed(2)}%`
            : val > 1000
            ? Number(val).toLocaleString()
            : val.toFixed(2);

          return (
            <div key={i} className="flex items-center justify-between gap-3 font-mono">
              <span className="flex items-center gap-1.5 text-on-surface-variant">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: entry.color || PALETTE[i % PALETTE.length] }}
                />
                <span>{entry.name}</span>
              </span>
              <span className="font-bold text-on-surface">{formatted}</span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div
      className={`bg-surface-container-low border border-outline-variant/30 rounded-2xl p-5 sm:p-6 shadow-sm flex flex-col gap-5 ${className}`}
    >
      {/* 1. Header: Auto-Detection Banner & Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-outline-variant/20">
        <div className="flex flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-secondary/10 border border-secondary/30 text-secondary text-[11px] font-mono font-semibold">
              <span className="material-symbols-outlined text-[13px] text-secondary">
                auto_awesome
              </span>
              <span>AUTO-DETECTED</span>
              <span className="text-outline">•</span>
              <span>{detection.confidence}% Match</span>
            </span>

            <button
              onClick={() => setShowReasoning((prev) => !prev)}
              className="text-[11px] font-mono text-outline hover:text-on-surface flex items-center gap-1 underline underline-offset-2 transition-colors"
            >
              <span>Why {getChartLabel(detection.recommendedChart)}?</span>
              <span className="material-symbols-outlined text-[13px]">
                {showReasoning ? 'expand_less' : 'expand_more'}
              </span>
            </button>
          </div>

          <h3 className="text-base sm:text-lg font-semibold text-on-surface">
            {title || `${detection.categoryLabel} ${activeMetric.label} Analysis`}
          </h3>
          <p className="text-xs text-on-surface-variant">
            {subtitle || `Visualizing ${chartData.length} records with automatic type formatting`}
          </p>
        </div>

        {/* Action Toolbar: Chart Type Switcher & Metric Selector */}
        <div className="flex flex-wrap items-center gap-2.5 self-start lg:self-center">
          {/* Metric Selector (if multiple available) */}
          {detection.availableMetrics.length > 1 && (
            <div className="flex items-center gap-1.5 bg-surface-container rounded-xl p-1 border border-outline-variant/20 text-xs">
              <span className="text-[10px] font-mono uppercase text-outline px-2 hidden sm:inline">
                Metric:
              </span>
              {detection.availableMetrics.slice(0, 3).map((metric) => {
                const isActive = metric.key === activeMetric.key;
                return (
                  <button
                    key={metric.key}
                    type="button"
                    onClick={() => setSelectedMetricKey(metric.key)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-mono transition-all ${
                      isActive
                        ? 'bg-primary text-on-primary font-bold shadow-sm'
                        : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high'
                    }`}
                  >
                    {metric.label}
                  </button>
                );
              })}
            </div>
          )}

          {/* Chart View Switcher */}
          <div className="flex items-center gap-1 bg-surface-container rounded-xl p-1 border border-outline-variant/20">
            {detection.supportedCharts.map((type) => {
              const isSelected = selectedChartType === type;
              const isOptimal = detection.recommendedChart === type;

              return (
                <button
                  key={type}
                  type="button"
                  onClick={() => setSelectedChartType(type)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs transition-all ${
                    isSelected
                      ? 'bg-surface-container-highest text-on-surface font-semibold shadow-sm ring-1 ring-primary/30'
                      : 'text-outline hover:text-on-surface hover:bg-surface-container-high'
                  }`}
                  title={`${getChartLabel(type)}${isOptimal ? ' (Auto-Recommended)' : ''}`}
                >
                  <span
                    className={`material-symbols-outlined text-[15px] ${
                      isSelected ? 'text-primary' : 'text-outline'
                    }`}
                  >
                    {getChartIcon(type)}
                  </span>
                  <span className="hidden md:inline">{getChartLabel(type)}</span>
                  {isOptimal && (
                    <span className="w-1.5 h-1.5 rounded-full bg-secondary" title="Recommended" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Sort toggle for ranked views */}
          {selectedChartType === 'ranked-bar' && !detection.temporalKey && (
            <button
              type="button"
              onClick={() =>
                setSortOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'))
              }
              className="p-1.5 rounded-xl bg-surface-container hover:bg-surface-container-high border border-outline-variant/20 text-outline hover:text-on-surface transition-colors"
              title={`Sort: ${sortOrder === 'desc' ? 'Descending' : 'Ascending'}`}
            >
              <span className="material-symbols-outlined text-[16px]">
                {sortOrder === 'desc' ? 'arrow_downward' : 'arrow_upward'}
              </span>
            </button>
          )}
        </div>
      </div>

      {/* Auto-Detection Explanation Drawer */}
      <AnimatePresence>
        {showReasoning && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="bg-surface-container/60 border border-primary/20 rounded-xl p-3.5 flex items-start gap-3 text-xs">
              <span className="material-symbols-outlined text-primary text-[18px] flex-shrink-0 mt-0.5">
                psychology
              </span>
              <div className="flex flex-col gap-1">
                <span className="font-semibold text-on-surface font-mono">
                  Autonomous Visualization Logic:
                </span>
                <p className="text-on-surface-variant leading-relaxed">
                  {detection.reason}
                </p>
                <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono text-outline pt-1">
                  <span>Entity Dimension: {detection.categoryKey}</span>
                  <span>•</span>
                  <span>Primary Metric: {activeMetric.label}</span>
                  <span>•</span>
                  <span>Records: {chartData.length}</span>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 2. Interactive Responsive Chart Stage */}
      <div className="w-full h-[340px] relative">
        <ResponsiveContainer width="100%" height="100%">
          {/* A. RANKED BAR CHART (Horizontal / Vertical) */}
          {selectedChartType === 'ranked-bar' ? (
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 10, right: 30, left: 70, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#292a2f" horizontal={false} />
              <XAxis
                type="number"
                stroke="#908fa0"
                fontSize={11}
                tickLine={false}
                tickFormatter={(val) =>
                  activeMetric.type === 'percentage'
                    ? `${val}%`
                    : val > 1000
                    ? `${(val / 1000).toFixed(0)}k`
                    : String(val)
                }
              />
              <YAxis
                type="category"
                dataKey="__displayName"
                stroke="#c7c4d7"
                fontSize={12}
                tickLine={false}
                width={85}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine
                x={avgValue}
                stroke="#8083ff"
                strokeDasharray="4 4"
                label={{
                  value: `Mean: ${activeMetric.format(avgValue)}`,
                  position: 'top',
                  fill: '#8083ff',
                  fontSize: 10,
                  fontFamily: 'monospace',
                }}
              />
              <Bar
                dataKey={activeMetric.key}
                name={activeMetric.label}
                radius={[0, 8, 8, 0]}
                barSize={20}
              >
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={
                      index === 0
                        ? '#4edea3' // #1 outlier highlight in emerald
                        : index === 1
                        ? '#60a5fa' // #2 runner-up in sky blue
                        : '#8083ff' // remaining in clean lavender indigo
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          ) : /* B. GROUPED COMPARISON BARS (e.g. Base vs Current) */
          selectedChartType === 'grouped-bar' ? (
            <BarChart
              data={chartData}
              margin={{ top: 15, right: 20, left: 10, bottom: 25 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#292a2f" vertical={false} />
              <XAxis
                dataKey="__displayName"
                stroke="#908fa0"
                fontSize={11}
                tickLine={false}
                angle={-15}
                textAnchor="end"
                height={40}
              />
              <YAxis
                stroke="#908fa0"
                fontSize={11}
                tickLine={false}
                tickFormatter={(val) =>
                  activeMetric.type === 'percentage' ? `${val}%` : String(val)
                }
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                verticalAlign="top"
                align="right"
                wrapperStyle={{ paddingBottom: '10px', fontSize: '11px' }}
              />
              {detection.comparisonMetric && (
                <Bar
                  dataKey={detection.comparisonMetric.key}
                  name={`Baseline Rate (${detection.comparisonMetric.label})`}
                  fill="#464554"
                  radius={[4, 4, 0, 0]}
                />
              )}
              <Bar
                dataKey={
                  data[0]?.currentRate !== undefined ? 'currentRate' : activeMetric.key
                }
                name="Current Observed Rate"
                fill="#4edea3"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          ) : /* C. TIME-SERIES / AREA TREND */
          selectedChartType === 'time-series' ? (
            <AreaChart
              data={chartData}
              margin={{ top: 15, right: 25, left: 10, bottom: 10 }}
            >
              <defs>
                <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4edea3" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#4edea3" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#292a2f" vertical={false} />
              <XAxis
                dataKey={detection.temporalKey || '__displayName'}
                stroke="#908fa0"
                fontSize={11}
                tickLine={false}
              />
              <YAxis
                stroke="#908fa0"
                fontSize={11}
                tickLine={false}
                tickFormatter={(val) =>
                  activeMetric.type === 'percentage' ? `${val}%` : String(val)
                }
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey={activeMetric.key}
                name={activeMetric.label}
                stroke="#4edea3"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#areaGradient)"
              />
            </AreaChart>
          ) : /* D. DONUT / PROPORTIONAL DISTRIBUTION */
          selectedChartType === 'donut' ? (
            <PieChart margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
              <Tooltip content={<CustomTooltip />} />
              <Pie
                data={chartData}
                dataKey={activeMetric.key}
                nameKey="__displayName"
                cx="50%"
                cy="50%"
                innerRadius={65}
                outerRadius={105}
                paddingAngle={3}
                label={({ name, percent }) =>
                  `${name}: ${(percent * 100).toFixed(1)}%`
                }
                labelLine={false}
              >
                {chartData.map((_, index) => (
                  <Cell
                    key={`pie-cell-${index}`}
                    fill={PALETTE[index % PALETTE.length]}
                    stroke="#1a1b21"
                    strokeWidth={2}
                  />
                ))}
              </Pie>
            </PieChart>
          ) : /* E. COMPOSED DUAL-AXIS (Volume Bars + Rate Line) */
          selectedChartType === 'composed' ? (
            <ComposedChart
              data={chartData}
              margin={{ top: 15, right: 35, left: 10, bottom: 25 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#292a2f" vertical={false} />
              <XAxis
                dataKey="__displayName"
                stroke="#908fa0"
                fontSize={11}
                tickLine={false}
                angle={-15}
                textAnchor="end"
                height={40}
              />
              {/* Left axis: Workers / Volume */}
              <YAxis
                yAxisId="left"
                stroke="#8083ff"
                fontSize={10}
                tickLine={false}
                tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`}
              />
              {/* Right axis: Percentage surge */}
              <YAxis
                yAxisId="right"
                orientation="right"
                stroke="#4edea3"
                fontSize={10}
                tickLine={false}
                tickFormatter={(val) => `${val}%`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                verticalAlign="top"
                align="right"
                wrapperStyle={{ paddingBottom: '10px', fontSize: '11px' }}
              />
              <Bar
                yAxisId="left"
                dataKey={detection.secondaryMetric?.key || 'estImpact'}
                name={detection.secondaryMetric?.label || 'Workers Affected'}
                fill="#8083ff"
                fillOpacity={0.7}
                radius={[4, 4, 0, 0]}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey={activeMetric.key}
                name={activeMetric.label}
                stroke="#4edea3"
                strokeWidth={3}
                dot={{ r: 5, fill: '#4edea3', stroke: '#121318', strokeWidth: 2 }}
              />
            </ComposedChart>
          ) : (
            <div className="w-full h-full flex items-center justify-center text-outline text-xs">
              Select a valid chart view above.
            </div>
          )}
        </ResponsiveContainer>
      </div>

      {/* 3. Bottom Summary Insights Strip */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-outline-variant/15 text-xs font-mono text-on-surface-variant">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 text-secondary">
            <span className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
            <span>Top Outlier: {chartData[0]?.__displayName}</span>
            <span className="font-bold">
              ({activeMetric.format(Number(chartData[0]?.[activeMetric.key]) || 0)})
            </span>
          </span>
          <span className="text-outline hidden sm:inline">•</span>
          <span className="text-outline hidden sm:inline">
            Mean: {activeMetric.format(avgValue)}
          </span>
        </div>

        <div className="flex items-center gap-2 text-outline text-[11px]">
          <span className="material-symbols-outlined text-[14px]">info</span>
          <span>Hover data points to inspect exact values</span>
        </div>
      </div>
    </div>
  );
};
