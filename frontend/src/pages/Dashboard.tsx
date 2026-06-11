import React, { useEffect } from 'react';
import { useVaultStore } from '../store/useVaultStore';
import { AlertCircle, Calendar, ShieldCheck } from 'lucide-react';

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export const Dashboard: React.FC = () => {
  const { stats, timelines, alerts, fetchStats, fetchTimelines, fetchAlerts } = useVaultStore();

  useEffect(() => {
    fetchStats();
    fetchTimelines();
    fetchAlerts();
  }, []);

  const chartData = stats?.category_counts
    ? Object.keys(stats.category_counts).map((key) => ({
        name: key.split(' ')[0], // Shorten name
        count: stats.category_counts[key],
      }))
    : [];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Intelligence Dashboard</h1>
        <p className="text-muted-foreground text-sm">
          A reasoning summary of your identity, academic history, and financial assets.
        </p>
      </div>

      {/* Overview Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Document count */}
        <div className="bg-card border border-border p-6 rounded-lg flex items-center justify-between shadow-sm">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Total Vault Files</p>
            <p className="text-3xl font-bold">{stats?.total_documents ?? 0}</p>
          </div>
          <ShieldCheck className="w-8 h-8 text-muted-foreground/40" />
        </div>

        {/* Health score */}
        <div className="bg-card border border-border p-6 rounded-lg flex items-center justify-between shadow-sm">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Document Health Score</p>
            <div className="flex items-baseline gap-2">
              <p className="text-3xl font-bold">{stats?.health_score ?? 0}%</p>
              <span className="text-xs text-muted-foreground">optimal vault metric</span>
            </div>
          </div>
          <div className="w-12 h-12 rounded-full border-4 border-muted flex items-center justify-center text-xs font-semibold relative">
            <div 
              className="absolute inset-0 rounded-full border-4 border-primary" 
              style={{ clipPath: `polygon(0 0, 100% 0, 100% ${stats?.health_score ?? 0}%, 0 ${stats?.health_score ?? 0}%)` }} 
            />
            {stats?.health_score ?? 0}%
          </div>
        </div>

        {/* Action alerts count */}
        <div className="bg-card border border-border p-6 rounded-lg flex items-center justify-between shadow-sm">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Renewal Tasks</p>
            <p className="text-3xl font-bold">{alerts.length}</p>
          </div>
          <Calendar className="w-8 h-8 text-muted-foreground/40" />
        </div>
      </div>

      {/* Missing Documents Warning Banner */}
      {stats && stats.missing_key_documents.length > 0 && (
        <div className="bg-secondary/40 border border-border p-4 rounded-lg flex items-start gap-4">
          <AlertCircle className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
          <div className="space-y-1">
            <p className="text-sm font-semibold">Incomplete Vault Profile</p>
            <p className="text-xs text-muted-foreground">
              To achieve a 100% Document Health Score, consider uploading: {' '}
              <span className="font-medium text-foreground">
                {stats.missing_key_documents.join(', ')}
              </span>
            </p>
          </div>
        </div>
      )}

      {/* Grid: Category Chart & Expiry Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Category breakdown bar chart */}
        <div className="bg-card border border-border p-6 rounded-lg space-y-4 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Vault Category Distribution</h2>
          {chartData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ left: -20 }}>
                  <XAxis dataKey="name" fontSize={11} stroke="var(--border)" />
                  <YAxis allowDecimals={false} fontSize={11} stroke="var(--border)" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'var(--card)', 
                      borderColor: 'var(--border)',
                      fontSize: '12px' 
                    }} 
                  />
                  <Bar dataKey="count" fill="hsl(var(--primary))" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center border border-dashed border-border rounded text-xs text-muted-foreground">
              No data uploaded yet.
            </div>
          )}
        </div>

        {/* Expiry alerts list */}
        <div className="bg-card border border-border p-6 rounded-lg space-y-4 shadow-sm flex flex-col justify-between">
          <div className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Expiry & Renewal Alerts</h2>
            {alerts.length > 0 ? (
              <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
                {alerts.map((alert) => (
                  <div 
                    key={alert.document_id} 
                    className="flex items-center justify-between p-3 border border-border rounded-lg bg-background/50 hover:bg-background transition-colors"
                  >
                    <div className="space-y-0.5">
                      <p className="text-xs font-semibold">{alert.name}</p>
                      <p className="text-[10px] text-muted-foreground">{alert.document_type}</p>
                    </div>
                    <div className="text-right space-y-0.5">
                      <span className={`text-[10px] px-2 py-0.5 rounded font-medium ${
                        alert.priority === 'high' 
                          ? 'bg-red-50 text-red-800 dark:bg-red-950/20 dark:text-red-400' 
                          : 'bg-yellow-50 text-yellow-800 dark:bg-yellow-950/20 dark:text-yellow-400'
                      }`}>
                        {alert.days_remaining} days left
                      </span>
                      <p className="text-[10px] text-muted-foreground">Expires: {alert.expiry_date}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center border border-dashed border-border rounded text-xs text-muted-foreground py-16">
                All documents are valid. No upcoming renewals.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Double Timeline: Academic & Career */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Academic Timeline */}
        <div className="bg-card border border-border p-6 rounded-lg space-y-6 shadow-sm">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Academic Timeline</h2>
            <p className="text-xs text-muted-foreground">Educational marksheet sequence extracted from vault documents.</p>
          </div>
          {timelines?.academic && timelines.academic.length > 0 ? (
            <div className="relative border-l border-border pl-6 ml-2 space-y-8">
              {timelines.academic.map((item) => (
                <div key={item.id} className="relative">
                  {/* Point */}
                  <span className="absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full bg-primary border-4 border-card" />
                  <div className="space-y-1">
                    <div className="flex items-baseline justify-between gap-4">
                      <h3 className="text-xs font-bold text-foreground">{item.name}</h3>
                      <span className="text-[10px] font-semibold text-muted-foreground">{item.year}</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground">{item.document_type}</p>
                    {item.detail && <p className="text-[11px] text-muted-foreground mt-1">{item.detail}</p>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-16 text-center border border-dashed border-border rounded text-xs text-muted-foreground">
              No academic records completed.
            </div>
          )}
        </div>

        {/* Career Timeline */}
        <div className="bg-card border border-border p-6 rounded-lg space-y-6 shadow-sm">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Career Timeline</h2>
            <p className="text-xs text-muted-foreground">Professional trajectory auto-assembled from offer letters and resumes.</p>
          </div>
          {timelines?.career && timelines.career.length > 0 ? (
            <div className="relative border-l border-border pl-6 ml-2 space-y-8">
              {timelines.career.map((item) => (
                <div key={item.id} className="relative">
                  {/* Point */}
                  <span className="absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full bg-muted-foreground/40 border-4 border-card" />
                  <div className="space-y-1">
                    <div className="flex items-baseline justify-between gap-4">
                      <h3 className="text-xs font-bold text-foreground">{item.company}</h3>
                      <span className="text-[10px] font-semibold text-muted-foreground">{item.date}</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground">{item.designation} {item.ctc ? `• ${item.ctc}` : ''}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-16 text-center border border-dashed border-border rounded text-xs text-muted-foreground">
              No professional records completed.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
