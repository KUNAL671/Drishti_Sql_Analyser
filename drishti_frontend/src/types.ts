export type PageId = 
  | 'new-analysis'
  | 'workspace-and-analysis'
  | 'query-history'
  | 'datasets'
  | 'schema-explorer'
  | 'settings';

export type BubbleState = 
  | 'idle'
  | 'thinking'
  | 'scanning'
  | 'generating'
  | 'validating'
  | 'executing'
  | 'verified'
  | 'error'
  | 'follow-up';

export interface AnalysisStage {
  id: number;
  title: string;
  detail: string;
  duration?: string;
  status: 'pending' | 'active' | 'completed' | 'error';
}

export interface DistrictDataRow {
  rank: number;
  district: string;
  zone: string;
  state: string;
  previousRate: number; // e.g. 8.2%
  currentRate: number;  // e.g. 12.5%
  deltaSurge: number;   // +4.3%
  estImpact: number;    // e.g. 248120
  alertTier: 'Critical' | 'High' | 'Elevated' | 'Moderate';
}

export interface ConversationMessage {
  id: string;
  sender: 'user' | 'drishti';
  text: string;
  timestamp: string;
  resultSnapshot?: {
    query: string;
    headline: string;
    summary: string;
    rows: DistrictDataRow[];
    sql: string;
    runtime: string;
    confidence: string;
  };
}

export interface DatasetItem {
  id: string;
  title: string;
  tablePath: string;
  type: 'PostgreSQL Table' | 'CSV / Parquet' | 'API Stream';
  status: string;
  activeInSession?: boolean;
  rows: string;
  columns: number;
  size: string;
  qualityScore: string;
  validationPct: number;
  updatedAt: string;
}

export interface ColumnDefinition {
  name: string;
  type: string;
  nullability: 'NOT NULL' | 'NULLABLE';
  semanticRole: string;
  boundsOrSample: string;
  indexOrConstraint: string;
  icon: string;
  isPrimaryKey?: boolean;
  isMetric?: boolean;
}
