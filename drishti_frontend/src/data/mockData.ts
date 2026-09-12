import { DistrictDataRow, DatasetItem, ColumnDefinition } from '../types';

export const INITIAL_DISTRICT_RESULTS: DistrictDataRow[] = [];
export const STATE_BREAKDOWN_RESULTS: DistrictDataRow[] = [];

export interface TimeSeriesPoint {
  year: number;
  value: number;
}

export const TIME_SERIES_TREND_RESULTS: Record<string, any>[] = [];
export const ZONE_DISTRIBUTION_RESULTS: Record<string, any>[] = [];

export const SCHEMA_COLUMNS: ColumnDefinition[] = [
  {
    name: 'id',
    type: 'INT',
    nullability: 'NOT NULL',
    semanticRole: 'Primary Key',
    boundsOrSample: '1, 2, 3...',
    indexOrConstraint: 'PRIMARY KEY',
    icon: 'fingerprint',
    isPrimaryKey: true
  },
  {
    name: 'name',
    type: 'VARCHAR(255)',
    nullability: 'NULLABLE',
    semanticRole: 'Entity Name',
    boundsOrSample: '"Alpha", "Beta"',
    indexOrConstraint: 'INDEXED',
    icon: 'label'
  },
  {
    name: 'value',
    type: 'NUMERIC',
    nullability: 'NULLABLE',
    semanticRole: 'Metric',
    boundsOrSample: '0 - 100',
    indexOrConstraint: 'None',
    icon: 'analytics',
    isMetric: true
  }
];

export const RECOMMENDED_QUERIES = [
  {
    category: 'Analysis',
    categoryClass: 'bg-[#4edea3]/10 text-[#4edea3]',
    title: 'Analyze distribution of value across name',
    tables: 'dataset',
    confidence: '99.4% confidence'
  }
];
