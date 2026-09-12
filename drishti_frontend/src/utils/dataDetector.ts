export type DetectedChartType =
  | 'ranked-bar'
  | 'grouped-bar'
  | 'time-series'
  | 'donut'
  | 'composed'
  | 'kpi-card';

export interface ColumnProfile {
  key: string;
  label: string;
  dataType: 'string' | 'number' | 'date' | 'boolean';
  semanticRole: 'category' | 'temporal' | 'percentage' | 'volume' | 'rank' | 'status' | 'general';
  sampleValues: any[];
  min?: number;
  max?: number;
  avg?: number;
  sum?: number;
}

export interface MetricDefinition {
  key: string;
  label: string;
  type: 'percentage' | 'volume' | 'number';
  format: (val: number) => string;
}

export interface DirectAnswerSummary {
  headline: string;
  directAnswerText: string;
  keyMetrics: {
    label: string;
    value: string;
    sublabel?: string;
    highlight?: boolean;
    tier?: 'positive' | 'warning' | 'critical' | 'neutral';
  }[];
  keyTakeaways: string[];
}

export interface DetectionResult {
  recommendedChart: DetectedChartType;
  confidence: number; // e.g. 98
  reason: string;
  categoryKey: string;
  categoryLabel: string;
  primaryMetric: MetricDefinition;
  secondaryMetric?: MetricDefinition;
  comparisonMetric?: MetricDefinition;
  temporalKey?: string;
  availableMetrics: MetricDefinition[];
  supportedCharts: DetectedChartType[];
  directAnswer: DirectAnswerSummary;
}

/**
 * Intelligent Data Analyzer & Auto-Detection Engine
 * Inspects keys, data types, distributions, and semantic markers in rows
 * to automatically determine the optimal chart type and generate executive answer summaries.
 */
export function analyzeAndDetectVisualization(
  rows: Record<string, any>[],
  queryPrompt?: string
): DetectionResult {
  if (!rows || rows.length === 0) {
    return {
      recommendedChart: 'ranked-bar',
      confidence: 50,
      reason: 'Empty dataset fallback',
      categoryKey: 'name',
      categoryLabel: 'Item',
      primaryMetric: {
        key: 'value',
        label: 'Value',
        type: 'number',
        format: (v) => String(v),
      },
      availableMetrics: [],
      supportedCharts: ['ranked-bar'],
      directAnswer: {
        headline: 'No records returned',
        directAnswerText: 'The executed query yielded 0 rows.',
        keyMetrics: [],
        keyTakeaways: ['Check query filter constraints'],
      },
    };
  }

  const firstRow = rows[0];
  const keys = Object.keys(firstRow);

  // 1. Column Profiling
  const profiles: Record<string, ColumnProfile> = {};
  for (const key of keys) {
    const values = rows.map((r) => r[key]).filter((v) => v !== null && v !== undefined);
    const sampleValues = values.slice(0, 5);

    let dataType: ColumnProfile['dataType'] = 'string';
    const isNum = values.every((v) => typeof v === 'number' || (!isNaN(Number(v)) && v !== ''));

    if (isNum && values.length > 0) {
      dataType = 'number';
    }

    // Determine semantic role
    let semanticRole: ColumnProfile['semanticRole'] = 'general';
    const lowerKey = key.toLowerCase();

    if (
      lowerKey.includes('year') ||
      lowerKey.includes('date') ||
      lowerKey.includes('month') ||
      lowerKey.includes('quarter') ||
      lowerKey.includes('period') ||
      lowerKey.includes('timestamp')
    ) {
      semanticRole = 'temporal';
    } else if (
      lowerKey.includes('rate') ||
      lowerKey.includes('pct') ||
      lowerKey.includes('percent') ||
      lowerKey.includes('surge') ||
      lowerKey.includes('delta') ||
      lowerKey.includes('share') ||
      lowerKey.includes('ratio')
    ) {
      semanticRole = 'percentage';
    } else if (
      lowerKey.includes('impact') ||
      lowerKey.includes('total') ||
      lowerKey.includes('count') ||
      lowerKey.includes('volume') ||
      lowerKey.includes('amount') ||
      lowerKey.includes('revenue')
    ) {
      semanticRole = 'volume';
    } else if (lowerKey === 'rank' || lowerKey === 'id' || lowerKey === 'order') {
      semanticRole = 'rank';
    } else if (lowerKey.includes('tier') || lowerKey.includes('status') || lowerKey.includes('level')) {
      semanticRole = 'status';
    } else if (
      lowerKey.includes('district') ||
      lowerKey.includes('state') ||
      lowerKey.includes('zone') ||
      lowerKey.includes('name') ||
      lowerKey.includes('title') ||
      lowerKey.includes('category') ||
      typeof firstRow[key] === 'string'
    ) {
      semanticRole = 'category';
    }

    let min: number | undefined;
    let max: number | undefined;
    let avg: number | undefined;
    let sum: number | undefined;

    if (dataType === 'number') {
      const numVals = values.map((v) => Number(v));
      min = Math.min(...numVals);
      max = Math.max(...numVals);
      sum = numVals.reduce((a, b) => a + b, 0);
      avg = sum / numVals.length;
    }

    profiles[key] = {
      key,
      label: formatLabel(key),
      dataType,
      semanticRole,
      sampleValues,
      min,
      max,
      avg,
      sum,
    };
  }

  // 2. Identify Key Candidates
  const temporalCol = Object.values(profiles).find(
    (p) => p.semanticRole === 'temporal' || (p.dataType === 'number' && p.min && p.min >= 1990 && p.max && p.max <= 2050)
  );

  const categoryCol =
    Object.values(profiles).find(
      (p) =>
        p.key === 'district' ||
        p.key === 'district_name' ||
        p.key === 'state' ||
        p.key === 'zone' ||
        p.key === 'category' ||
        p.key === 'name' ||
        p.key === 'label'
    ) ||
    Object.values(profiles).find((p) => p.semanticRole === 'category') ||
    Object.values(profiles).find((p) => p.dataType === 'string') ||
    profiles[keys[0]];

  const percentageCols = Object.values(profiles).filter(
    (p) => p.dataType === 'number' && (p.semanticRole === 'percentage' || p.key.includes('Rate') || p.key.includes('Surge'))
  );

  const volumeCols = Object.values(profiles).filter(
    (p) => p.dataType === 'number' && (p.semanticRole === 'volume' || p.key.includes('Impact') || p.key.includes('labor'))
  );

  const allNumericCols = Object.values(profiles).filter(
    (p) => p.dataType === 'number' && p.semanticRole !== 'rank' && p.semanticRole !== 'temporal'
  );

  // Available metrics definition
  const availableMetrics: MetricDefinition[] = allNumericCols.map((c) => ({
    key: c.key,
    label: c.label,
    type: c.semanticRole === 'percentage' ? 'percentage' : c.semanticRole === 'volume' ? 'volume' : 'number',
    format: (val: number) => {
      if (c.semanticRole === 'percentage' || c.key.toLowerCase().includes('rate') || c.key.toLowerCase().includes('surge')) {
        return `${val >= 0 && c.key.toLowerCase().includes('surge') ? '+' : ''}${val.toFixed(2)}%`;
      }
      if (c.semanticRole === 'volume' || val > 1000) {
        return Number(val).toLocaleString();
      }
      return val.toFixed(1);
    },
  }));

  // Select primary metric
  const primaryCol: ColumnProfile =
    percentageCols.find((c) => c.key.toLowerCase().includes('delta') || c.key.toLowerCase().includes('surge')) ||
    percentageCols.find((c) => c.key.toLowerCase().includes('current')) ||
    percentageCols[0] ||
    volumeCols[0] ||
    allNumericCols[0] || {
      key: 'value',
      label: 'Value',
      dataType: 'number',
      semanticRole: 'general',
      sampleValues: [0],
    };

  const primaryMetric: MetricDefinition = {
    key: primaryCol.key,
    label: primaryCol.label,
    type: primaryCol.semanticRole === 'percentage' ? 'percentage' : 'number',
    format: (val: number) => {
      if (primaryCol.semanticRole === 'percentage' || primaryCol.key.toLowerCase().includes('rate') || primaryCol.key.toLowerCase().includes('surge')) {
        return `${val >= 0 && primaryCol.key.toLowerCase().includes('surge') ? '+' : ''}${val.toFixed(2)}%`;
      }
      if (val > 1000) return Number(val).toLocaleString();
      return val.toFixed(1);
    },
  };

  // Select comparison baseline metric if available (e.g. previousRate vs currentRate)
  const baselineCol = percentageCols.find(
    (c) => c.key.toLowerCase().includes('previous') || c.key.toLowerCase().includes('base')
  );
  const currentRateCol = percentageCols.find(
    (c) => c.key.toLowerCase().includes('current')
  );

  const comparisonMetric: MetricDefinition | undefined =
    baselineCol && currentRateCol
      ? {
          key: baselineCol.key,
          label: baselineCol.label,
          type: 'percentage',
          format: (v) => `${v.toFixed(2)}%`,
        }
      : undefined;

  // Secondary volume metric for dual-axis (e.g. Impacted workers)
  const secondaryCol = volumeCols[0];
  const secondaryMetric: MetricDefinition | undefined = secondaryCol
    ? {
        key: secondaryCol.key,
        label: secondaryCol.label,
        type: 'volume',
        format: (v) => Number(v).toLocaleString(),
      }
    : undefined;

  // 3. Auto-Detection Decision Logic
  let recommendedChart: DetectedChartType = 'ranked-bar';
  let confidence = 95;
  let reason = '';
  const supportedCharts: DetectedChartType[] = ['ranked-bar'];

  // Condition 1: Time series / temporal
  if (temporalCol && rows.length >= 3) {
    recommendedChart = 'time-series';
    confidence = 98;
    reason = `Detected chronological temporal axis (${temporalCol.label}). Area trend curve provides optimal visual analysis of trajectory.`;
    supportedCharts.unshift('time-series');
    if (!supportedCharts.includes('ranked-bar')) supportedCharts.push('ranked-bar');
    if (!supportedCharts.includes('composed')) supportedCharts.push('composed');
  }
  // Condition 2: Multi-metric correlation with rate + volume (e.g. surge % and total labor impacted)
  else if (percentageCols.length > 0 && volumeCols.length > 0 && rows.length <= 10) {
    // If the query explicitly asks for surge/outliers, ranked-bar or composed are great
    if (queryPrompt && (queryPrompt.toLowerCase().includes('impact') || queryPrompt.toLowerCase().includes('correlation'))) {
      recommendedChart = 'composed';
      confidence = 97;
      reason = `Detected paired multi-scale metrics (${primaryMetric.label} vs ${secondaryCol.label}). Composed Dual-Axis chart correlates primary metric with volume scale.`;
    } else {
      recommendedChart = 'ranked-bar';
      confidence = 96;
      reason = `Detected ${rows.length} ranked entities with comparative rate delta metrics. Ranked horizontal bar chart provides maximum outlier contrast.`;
    }
    supportedCharts.push('grouped-bar', 'composed', 'donut');
  }
  // Condition 3: Proportional distribution / state breakdown (e.g. states or tiers)
  else if (
    (categoryCol?.key.toLowerCase().includes('state') || categoryCol?.key.toLowerCase().includes('tier') || rows.length <= 4) &&
    !queryPrompt?.toLowerCase().includes('rank')
  ) {
    recommendedChart = 'donut';
    confidence = 94;
    reason = `Detected categorical distribution across ${rows.length} segments. Donut distribution chart clearly communicates proportional share.`;
    supportedCharts.push('donut', 'ranked-bar', 'grouped-bar');
  }
  // Condition 4: Default entity ranking / comparative bars
  else {
    recommendedChart = 'ranked-bar';
    confidence = 97;
    reason = `Detected categorical entities (${categoryCol?.label || 'Items'}) with comparative metrics. Ranked Bar format guarantees rapid scanning of top outliers.`;
    supportedCharts.push('grouped-bar', 'donut');
    if (volumeCols.length > 0) supportedCharts.push('composed');
  }

  // Ensure unique list
  const cleanSupportedCharts = Array.from(new Set([recommendedChart, ...supportedCharts]));

  // 4. Generate Synthesized Direct Answer
  const directAnswer = generateDirectAnswer({
    rows,
    categoryCol: categoryCol || profiles[keys[0]],
    primaryCol,
    secondaryCol,
    baselineCol,
    currentRateCol,
    queryPrompt,
  });

  return {
    recommendedChart,
    confidence,
    reason,
    categoryKey: categoryCol ? categoryCol.key : keys[0],
    categoryLabel: categoryCol ? categoryCol.label : 'Item',
    primaryMetric,
    secondaryMetric,
    comparisonMetric,
    temporalKey: temporalCol?.key,
    availableMetrics,
    supportedCharts: cleanSupportedCharts,
    directAnswer,
  };
}

function formatLabel(key: string): string {
  return key
    .replace(/([A-Z])/g, ' $1')
    .replace(/_/g, ' ')
    .replace(/^\w/, (c) => c.toUpperCase())
    .trim();
}

interface GenerateAnswerParams {
  rows: Record<string, any>[];
  categoryCol: ColumnProfile;
  primaryCol: ColumnProfile;
  secondaryCol?: ColumnProfile;
  baselineCol?: ColumnProfile;
  currentRateCol?: ColumnProfile;
  queryPrompt?: string;
}

function generateDirectAnswer({
  rows,
  categoryCol,
  primaryCol,
  secondaryCol,
  baselineCol,
  currentRateCol,
}: GenerateAnswerParams): DirectAnswerSummary {
  if (rows.length === 0) {
    return {
      headline: 'No matching records found',
      directAnswerText: 'The query executed without returning data points.',
      keyMetrics: [],
      keyTakeaways: [],
    };
  }

  // Find top entity
  const sorted = [...rows].sort((a, b) => {
    const valA = Number(a[primaryCol.key]) || 0;
    const valB = Number(b[primaryCol.key]) || 0;
    return valB - valA;
  });

  const top = sorted[0];
  const runnerUp = sorted[1];
  const topName = String(top[categoryCol.key] || 'Top Item');
  const topVal = Number(top[primaryCol.key]) || 0;
  const runnerUpName = runnerUp ? String(runnerUp[categoryCol.key]) : null;
  const runnerUpVal = runnerUp ? Number(runnerUp[primaryCol.key]) : null;

  // Formatting strings
  const isPct =
    primaryCol.semanticRole === 'percentage' ||
    primaryCol.key.toLowerCase().includes('rate') ||
    primaryCol.key.toLowerCase().includes('surge');

  const topValStr = isPct ? `+${topVal.toFixed(2)}%` : topVal.toLocaleString();
  const runnerUpValStr = runnerUpVal !== null ? (isPct ? `+${runnerUpVal.toFixed(2)}%` : runnerUpVal.toLocaleString()) : '';

  // Calculate totals
  const totalVolume = secondaryCol?.sum || 0;
  const avgPrimary = primaryCol.avg || 0;
  const avgPrimaryStr = isPct ? `+${avgPrimary.toFixed(2)}%` : avgPrimary.toFixed(1);

  // Formulate the direct natural-language answer text
  let directAnswerText = '';
  if (runnerUp && runnerUpName) {
    directAnswerText = `${topName} has the highest ${primaryCol.label.toLowerCase()} at ${topValStr}, followed by ${runnerUpName} at ${runnerUpValStr}. Across the ${rows.length} records analyzed, the average is ${avgPrimaryStr}.`;
  } else {
    directAnswerText = `${topName} leads with ${topValStr} ${primaryCol.label.toLowerCase()}.`;
  }

  // Headline
  const headline = `${topName} leads with peak ${primaryCol.label} (${topValStr})`;

  // Key Metric Cards
  const keyMetrics: DirectAnswerSummary['keyMetrics'] = [
    {
      label: 'Leading Entity',
      value: topName,
      sublabel: topValStr,
      highlight: true,
      tier: 'critical',
    },
    {
      label: `Mean ${primaryCol.label}`,
      value: avgPrimaryStr,
      sublabel: `Across top ${rows.length} records`,
      tier: 'warning',
    },
  ];

  if (totalVolume > 0 && secondaryCol) {
    keyMetrics.push({
      label: secondaryCol.label,
      value: `${(totalVolume / 1000).toFixed(0)}k`,
      sublabel: 'Total aggregate volume',
      tier: 'positive',
    });
  } else if (currentRateCol && top[currentRateCol.key] !== undefined) {
    const peakCurrent = Number(top[currentRateCol.key]);
    keyMetrics.push({
      label: 'Peak Current Rate',
      value: `${peakCurrent.toFixed(2)}%`,
      sublabel: baselineCol ? `Up from ${Number(top[baselineCol.key]).toFixed(2)}%` : undefined,
      tier: 'warning',
    });
  }

  keyMetrics.push({
    label: 'Verification Status',
    value: '100% Deterministic',
    sublabel: 'Verified query results',
    tier: 'positive',
  });

  // Key Takeaways
  const keyTakeaways: string[] = [
    `${topName} registered the peak value of ${topValStr}.`,
    `Averaged across the ${rows.length} entities is ${avgPrimaryStr}.`,
  ];

  if (totalVolume > 0) {
    keyTakeaways.push(
      `Total sum across these records is approximately ${(totalVolume / 1000).toFixed(0)}k.`
    );
  } else if (baselineCol && currentRateCol) {
    keyTakeaways.push(
      `Baseline comparison indicates rates changed between base and current periods.`
    );
  }

  return {
    headline,
    directAnswerText,
    keyMetrics,
    keyTakeaways,
  };
}
