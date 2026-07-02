import React, { useEffect } from 'react';
import { useVaultStore } from '../store/useVaultStore';
import { Calendar, ShieldCheck, AlertTriangle } from 'lucide-react';
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
    <div className="flex flex-col h-full bg-[#F8FAFC] dark:bg-slate-950 overflow-y-auto">
      {/* Top Header Bar */}
      <header className="h-14 border-b border-[#E5E7EB] dark:border-slate-800 bg-white dark:bg-slate-900 px-8 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2 text-xs text-[#6B7280]">
          <span>Console</span>
          <span>/</span>
          <span className="text-[#111827] dark:text-slate-200 font-medium">Dashboard</span>
        </div>
      </header>

      {/* Main Content Box */}
      <div className="p-8 max-w-7xl w-full mx-auto space-y-8 flex-1">
        
        {/* Title */}
        <div>
          <h1 className="text-24px font-semibold text-[#111827] dark:text-slate-100 tracking-tight">
            Intelligence Dashboard
          </h1>
          <p className="text-xs text-[#6B7280] dark:text-slate-400 mt-1">
            Overview metrics for credentials, academic trajectories, and security alerts.
          </p>
        </div>

        {/* Overview KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: Total Files */}
          <div className="bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 p-6 rounded shadow-[0_1px_2px_rgba(0,0,0,0.01)] flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-[10px] font-bold text-[#6B7280] dark:text-slate-400 uppercase tracking-wider">Total Vault Files</p>
              <p className="text-2xl font-semibold text-[#111827] dark:text-slate-100">{stats?.total_documents ?? 0}</p>
            </div>
            <div className="p-2.5 bg-[#F3F4F6] dark:bg-slate-800 text-[#6B7280] dark:text-slate-400 rounded">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>

          {/* Card 2: Health Score */}
          <div className="bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 p-6 rounded shadow-[0_1px_2px_rgba(0,0,0,0.01)] space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] font-bold text-[#6B7280] dark:text-slate-400 uppercase tracking-wider">Vault Integrity</p>
                <p className="text-2xl font-semibold text-[#111827] dark:text-slate-100">{stats?.health_score ?? 0}%</p>
              </div>
              <span className="text-[10px] text-[#6B7280] dark:text-slate-400 font-medium">Standard Cover</span>
            </div>
            {/* Minimalist Linear Progress Bar */}
            <div className="w-full bg-[#E5E7EB] dark:bg-slate-800 h-1.5 rounded overflow-hidden">
              <div 
                className="bg-[#2563EB] h-full rounded transition-all duration-500" 
                style={{ width: `${stats?.health_score ?? 0}%` }}
              />
            </div>
          </div>

          {/* Card 3: Action Alerts */}
          <div className="bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 p-6 rounded shadow-[0_1px_2px_rgba(0,0,0,0.01)] flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-[10px] font-bold text-[#6B7280] dark:text-slate-400 uppercase tracking-wider">Renewal Alerts</p>
              <p className="text-2xl font-semibold text-[#111827] dark:text-slate-100">{alerts.length}</p>
            </div>
            <div className="p-2.5 bg-[#F3F4F6] dark:bg-slate-800 text-[#6B7280] dark:text-slate-400 rounded">
              <Calendar className="w-5 h-5" />
            </div>
          </div>
        </div>

        {/* Warning Banner for Missing Key Documents */}
        {stats && stats.missing_key_documents.length > 0 && (
          <div className="bg-[#F59E0B]/5 border-l-2 border-[#F59E0B] p-4 rounded flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-[#F59E0B] flex-shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <p className="text-xs font-semibold text-[#111827] dark:text-slate-200">Recommended Uploads</p>
              <p className="text-[11px] text-[#6B7280] dark:text-slate-400">
                To maximize your profile coverage, consider uploading: {' '}
                <span className="font-semibold text-[#111827] dark:text-slate-350">
                  {stats.missing_key_documents.join(', ')}
                </span>
              </p>
            </div>
          </div>
        )}

        {/* Category Breakdown & Expirations */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Chart Panel */}
          <div className="bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 p-6 rounded shadow-[0_1px_2px_rgba(0,0,0,0.01)] space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-[#6B7280]">
              Vault Category Distribution
            </h2>
            {chartData.length > 0 ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ left: -24 }}>
                    <XAxis dataKey="name" fontSize={10} stroke="#94A3B8" tickLine={false} />
                    <YAxis allowDecimals={false} fontSize={10} stroke="#94A3B8" tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--card)',
                        borderColor: 'var(--border)',
                        fontSize: '11px',
                        borderRadius: '4px'
                      }}
                    />
                    <Bar dataKey="count" fill="#2563EB" radius={[2, 2, 0, 0]} barSize={36} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center border border-dashed border-[#E5E7EB] dark:border-slate-800 rounded text-xs text-[#6B7280]">
                No files uploaded yet.
              </div>
            )}
          </div>

          {/* Expiry alerts list */}
          <div className="bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 p-6 rounded shadow-[0_1px_2px_rgba(0,0,0,0.01)] space-y-4 flex flex-col justify-between">
            <div className="space-y-4 w-full">
              <h2 className="text-xs font-bold uppercase tracking-wider text-[#6B7280]">
                Upcoming Expirations & Renewals
              </h2>
              {alerts.length > 0 ? (
                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {alerts.map((alert) => (
                    <div
                      key={alert.document_id}
                      className="flex items-center justify-between p-3 border border-[#E5E7EB] dark:border-slate-800 rounded bg-white dark:bg-slate-950/40 hover:bg-[#F3F4F6] dark:hover:bg-slate-850 transition-colors"
                    >
                      <div className="space-y-0.5">
                        <p className="text-xs font-semibold text-[#111827] dark:text-slate-200">{alert.name}</p>
                        <p className="text-[10px] text-[#6B7280] dark:text-slate-400">{alert.document_type}</p>
                      </div>
                      <div className="text-right space-y-0.5">
                        <span className={`nv-badge ${
                          alert.priority === 'high'
                            ? 'nv-badge-danger'
                            : 'nv-badge-warning'
                        }`}>
                          {alert.days_remaining} days left
                        </span>
                        <p className="text-[10px] text-[#6B7280] dark:text-slate-400 font-medium">Expires: {alert.expiry_date}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center border border-dashed border-[#E5E7EB] dark:border-slate-800 rounded text-xs text-[#6B7280] py-16">
                  All documents are currently valid.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Timelines Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Academic Timeline */}
          <div className="bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 p-6 rounded shadow-[0_1px_2px_rgba(0,0,0,0.01)] space-y-6">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-[#6B7280]">Academic Progression</h2>
              <p className="text-[11px] text-[#6B7280] dark:text-slate-400 mt-0.5">Academic milestones parsed from educational credentials.</p>
            </div>
            {timelines?.academic && timelines.academic.length > 0 ? (
              <div className="relative border-l border-[#E5E7EB] dark:border-slate-800 pl-6 ml-2 space-y-6">
                {timelines.academic.map((item) => (
                  <div key={item.id} className="relative">
                    <span className="absolute -left-[30px] top-1 w-2.5 h-2.5 rounded-full bg-[#2563EB] border-2 border-white dark:border-slate-900" />
                    <div className="space-y-0.5">
                      <div className="flex items-baseline justify-between gap-4">
                        <h3 className="text-xs font-semibold text-[#111827] dark:text-slate-200">{item.name}</h3>
                        <span className="text-[10px] text-[#6B7280] dark:text-slate-400 font-bold">{item.year}</span>
                      </div>
                      <p className="text-[10px] text-[#6B7280] dark:text-slate-400">{item.document_type}</p>
                      {item.detail && <p className="text-[11px] text-[#6B7280] dark:text-slate-400 mt-1 italic">{item.detail}</p>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-12 text-center border border-dashed border-[#E5E7EB] dark:border-slate-800 rounded text-xs text-[#6B7280]">
                No academic records processed yet.
              </div>
            )}
          </div>

          {/* Career Timeline */}
          <div className="bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 p-6 rounded shadow-[0_1px_2px_rgba(0,0,0,0.01)] space-y-6">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-[#6B7280]">Professional Progression</h2>
              <p className="text-[11px] text-[#6B7280] dark:text-slate-400 mt-0.5">Career milestone assembly parsed from professional credentials.</p>
            </div>
            {timelines?.career && timelines.career.length > 0 ? (
              <div className="relative border-l border-[#E5E7EB] dark:border-slate-800 pl-6 ml-2 space-y-6">
                {timelines.career.map((item) => (
                  <div key={item.id} className="relative">
                    <span className="absolute -left-[30px] top-1 w-2.5 h-2.5 rounded-full bg-[#6B7280] border-2 border-white dark:border-slate-900" />
                    <div className="space-y-0.5">
                      <div className="flex items-baseline justify-between gap-4">
                        <h3 className="text-xs font-semibold text-[#111827] dark:text-slate-200">{item.company}</h3>
                        <span className="text-[10px] text-[#6B7280] dark:text-slate-400 font-bold">{item.date}</span>
                      </div>
                      <p className="text-[10px] text-[#6B7280] dark:text-slate-400">{item.designation} {item.ctc ? `• ${item.ctc}` : ''}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-12 text-center border border-dashed border-[#E5E7EB] dark:border-slate-800 rounded text-xs text-[#6B7280]">
                No professional trajectory milestones recorded.
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
