import { useState } from 'react';
import { motion } from 'motion/react';
import { SCHEMA_COLUMNS } from '../data/mockData';

interface SchemaExplorerViewProps {
  onNewQueryWithColumn?: (colName: string) => void;
}

export const SchemaExplorerView = ({ onNewQueryWithColumn }: SchemaExplorerViewProps) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState<'columns' | 'relations' | 'safety'>('columns');

  const filteredColumns = SCHEMA_COLUMNS.filter(
    (col) =>
      col.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      col.semanticRole.toLowerCase().includes(searchTerm.toLowerCase()) ||
      col.type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="w-full max-w-6xl mx-auto px-8 sm:px-12 py-10 sm:py-14 flex flex-col gap-8">
      {/* Spacious Open Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 pb-2">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-primary text-[24px]">account_tree</span>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-on-surface">
              Schema Explorer & AST Mapping
            </h1>
          </div>
          <p className="text-sm text-on-surface-variant font-normal leading-relaxed">
            Table: <span className="text-primary font-mono font-medium">Active Dataset</span> • {SCHEMA_COLUMNS.length} Columns Indexed
          </p>
        </div>

        {/* Search */}
        <div className="flex items-center gap-2.5 bg-surface-container-low px-4 py-2.5 rounded-xl border border-outline-variant/30 text-sm text-on-surface w-full sm:w-72 shadow-sm">
          <span className="material-symbols-outlined text-[18px] text-outline">search</span>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search columns, types..."
            className="bg-transparent focus:outline-none w-full placeholder:text-outline text-sm"
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-3 border-b border-outline-variant/20 pb-2">
        {[
          { id: 'columns' as const, label: 'Column Dictionary & Bounds', icon: 'view_column' },
          { id: 'relations' as const, label: 'Relations Graph', icon: 'hub' },
          { id: 'safety' as const, label: 'Security & Safety Bounds', icon: 'shield' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-primary/15 text-primary border border-primary/30 font-semibold shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low'
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Main Tab Content */}
      {activeTab === 'columns' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Columns Table (8 cols) */}
          <div className="lg:col-span-8 bg-surface-container-low border border-outline-variant/30 rounded-2xl shadow-sm overflow-hidden flex flex-col">
            <div className="px-6 py-3.5 bg-surface-container/70 border-b border-outline-variant/20 flex items-center justify-between text-xs font-mono text-on-surface-variant font-medium">
              <span>Column Name & Type</span>
              <span>Semantic Role & Bounds</span>
            </div>

            <div className="divide-y divide-outline-variant/15">
              {filteredColumns.map((col) => (
                <div
                  key={col.name}
                  className="p-6 hover:bg-surface-container/50 transition-colors flex flex-col gap-2.5 group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="material-symbols-outlined text-primary text-[20px]">{col.icon}</span>
                      <span className="font-mono text-sm text-on-surface font-semibold group-hover:text-primary transition-colors">
                        {col.name}
                      </span>
                      <span className="px-2.5 py-0.5 rounded-md bg-surface-container-highest text-[11px] font-mono text-outline">
                        {col.type}
                      </span>
                      {col.isPrimaryKey && (
                        <span className="px-2 py-0.5 rounded-full bg-secondary/15 text-secondary text-[10px] font-mono font-bold border border-secondary/30">
                          PK
                        </span>
                      )}
                    </div>

                    <span className="text-xs font-mono text-secondary font-medium">
                      {col.nullability}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center justify-between text-xs text-on-surface-variant font-mono gap-3 pl-8">
                    <span className="text-primary/90">{col.semanticRole}</span>
                    <span className="text-outline text-xs">{col.boundsOrSample}</span>
                    <span className="text-xs px-2.5 py-0.5 rounded bg-surface-container-lowest border border-outline-variant/15 text-outline">
                      {col.indexOrConstraint}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Catalog Health & Quick Stats Sidebar (4 cols) */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            <div className="bg-surface-container-low border border-outline-variant/30 rounded-2xl p-6 shadow-sm flex flex-col gap-4">
              <span className="text-xs uppercase tracking-wider text-on-surface font-semibold">
                Catalog Diagnostics
              </span>

              <div className="flex flex-col gap-2.5 text-xs font-mono">
                <div className="p-3 rounded-xl bg-surface-container flex items-center justify-between">
                  <span className="text-on-surface-variant">Completeness</span>
                  <span className="text-secondary font-bold">100%</span>
                </div>
                <div className="p-3 rounded-xl bg-surface-container flex items-center justify-between">
                  <span className="text-on-surface-variant">Null Keys Tolerated</span>
                  <span className="text-secondary font-bold">0 Violations</span>
                </div>
                <div className="p-3 rounded-xl bg-surface-container flex items-center justify-between">
                  <span className="text-on-surface-variant">BTREE Indexes</span>
                  <span className="text-primary font-bold">3 Active</span>
                </div>
                <div className="p-3 rounded-xl bg-surface-container flex items-center justify-between">
                  <span className="text-on-surface-variant">Coverage</span>
                  <span className="text-on-surface">2018 - 2024</span>
                </div>
              </div>
            </div>

            <div className="bg-surface-container-low border border-outline-variant/30 rounded-2xl p-6 shadow-sm flex flex-col gap-3">
              <span className="text-xs uppercase tracking-wider text-on-surface font-semibold">
                Quick Query Seeds
              </span>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                Click any column to seed a query:
              </p>
              <div className="flex flex-wrap gap-2 mt-1">
                {filteredColumns.slice(0, 3).map((c) => (
                  <button
                    key={c.name}
                    onClick={() => onNewQueryWithColumn?.(`Analyze distribution of ${c.name} across all categories`)}
                    className="px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-xs font-mono text-primary transition-colors border border-outline-variant/20"
                  >
                    + {c.name}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Automated Relations Graph Tab */}
      {activeTab === 'relations' && (
        <div className="bg-surface-container-low border border-outline-variant/30 rounded-2xl p-8 shadow-sm flex flex-col gap-6">
          <div className="flex items-center justify-between">
            <span className="text-lg font-semibold text-on-surface">
              Foreign Key & Semantic Relationship Topology
            </span>
            <span className="text-xs font-mono text-secondary">3 Nodes Auto-Linked</span>
          </div>

          <div className="w-full bg-surface-container-lowest rounded-2xl p-8 border border-outline-variant/20 flex flex-wrap items-center justify-around gap-8 py-16 relative overflow-hidden">
            {/* Primary Table Node */}
            <div className="w-64 bg-surface-container p-4 rounded-xl border border-primary/40 shadow-md flex flex-col gap-1.5 font-mono text-xs z-10">
              <span className="text-[10px] text-primary uppercase font-bold">Primary Fact Table</span>
              <span className="text-on-surface font-semibold text-sm">in_state_employment</span>
              <span className="text-[11px] text-outline">FK: state_code → states</span>
              <span className="text-[11px] text-outline">FK: zone_id → geo_zones</span>
            </div>

            {/* Connecting line */}
            <div className="w-16 h-0.5 bg-primary/40 relative hidden sm:block">
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 text-[9px] font-mono text-primary">1:N</span>
            </div>

            {/* Dimension Node 1 */}
            <div className="w-56 bg-surface-container p-4 rounded-xl border border-secondary/40 shadow-md flex flex-col gap-1.5 font-mono text-xs z-10">
              <span className="text-[10px] text-secondary uppercase font-bold">Dimension Table</span>
              <span className="text-on-surface font-semibold text-sm">states_master</span>
              <span className="text-[11px] text-outline">PK: state_code</span>
              <span className="text-[11px] text-outline">36 states & territories</span>
            </div>

            {/* Dimension Node 2 */}
            <div className="w-56 bg-surface-container p-4 rounded-xl border border-tertiary/40 shadow-md flex flex-col gap-1.5 font-mono text-xs z-10">
              <span className="text-[10px] text-tertiary uppercase font-bold">Dimension Table</span>
              <span className="text-on-surface font-semibold text-sm">geo_zones</span>
              <span className="text-[11px] text-outline">PK: zone_id</span>
              <span className="text-[11px] text-outline">6 economic corridors</span>
            </div>
          </div>
        </div>
      )}

      {/* Safety Bounds Tab */}
      {activeTab === 'safety' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-surface-container-low border border-outline-variant/30 rounded-2xl p-7 shadow-sm flex flex-col gap-3">
            <span className="material-symbols-outlined text-secondary text-[26px]">lock</span>
            <h3 className="text-base font-semibold text-on-surface">Read-Only Isolation</h3>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              Every query is wrapped in an explicit <code className="text-xs bg-surface-container px-1.5 py-0.5 rounded">BEGIN TRANSACTION READ ONLY;</code> block. All mutation operations are rejected at AST parsing before execution.
            </p>
          </div>

          <div className="bg-surface-container-low border border-outline-variant/30 rounded-2xl p-7 shadow-sm flex flex-col gap-3">
            <span className="material-symbols-outlined text-primary text-[26px]">timer</span>
            <h3 className="text-base font-semibold text-on-surface">Cost & Timeout Budget</h3>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              Queries are bounded by a strict 1,500ms execution timeout and 0.05 CPU-second threshold to guarantee replica stability.
            </p>
          </div>

          <div className="bg-surface-container-low border border-outline-variant/30 rounded-2xl p-7 shadow-sm flex flex-col gap-3">
            <span className="material-symbols-outlined text-tertiary text-[26px]">view_agenda</span>
            <h3 className="text-base font-semibold text-on-surface">Cardinality Cap</h3>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              Automatic LIMIT injection caps candidate record sets at 10,000 rows max, protecting the UI memory footprint.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
