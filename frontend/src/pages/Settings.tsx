import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../store/useAuthStore';
import { useVaultStore } from '../store/useVaultStore';
import { KeyRound, Clock, ShieldAlert } from 'lucide-react';

import api from '../services/api';

export const Settings: React.FC = () => {
  const { setupPin, error, clearError } = useAuthStore();
  const { fetchDocuments, fetchStats } = useVaultStore();

  const [pin, setPin] = useState('');
  const [pinConfirm, setPinConfirm] = useState('');
  const [pinMessage, setPinMessage] = useState<string | null>(null);
  const [pinErr, setPinErr] = useState<string | null>(null);
  
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  useEffect(() => {
    fetchAuditLogs();
    clearError();
  }, []);

  const fetchAuditLogs = async () => {
    setLoadingLogs(true);
    try {
      const response = await api.get('/api/auth/audit-logs');
      setAuditLogs(response.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingLogs(false);
    }
  };

  const handlePinSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPinErr(null);
    setPinMessage(null);

    if (pin.length < 4 || pin.length > 6 || !/^\d+$/.test(pin)) {
      setPinErr('PIN must be 4 to 6 numeric digits.');
      return;
    }

    if (pin !== pinConfirm) {
      setPinErr('PIN codes do not match.');
      return;
    }

    const success = await setupPin(pin);
    if (success) {
      setPinMessage('Secondary security PIN configured successfully.');
      setPin('');
      setPinConfirm('');
      fetchAuditLogs();
    } else {
      setPinErr(error || 'Failed to configure PIN.');
    }
  };

  const handleWipeVault = async () => {
    if (
      window.confirm(
        'DANGER: Are you sure you want to permanently delete all your documents, vector embeddings, and graph linkages? This action is irreversible.'
      )
    ) {
      try {
        // Fetch current documents and delete one by one
        const docsResponse = await api.get('/api/documents/');
        const docs = docsResponse.data;
        for (const doc of docs) {
          await api.delete(`/api/documents/${doc.id}`);
        }
        alert('Vault wiped successfully.');
        fetchDocuments();
        fetchStats();
        fetchAuditLogs();
      } catch (err) {
        alert('Failed to fully wipe vault.');
      }
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8 h-full overflow-y-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Security & Settings</h1>
        <p className="text-muted-foreground text-sm">
          Manage PIN locks, inspect file access audits, and configure compliance profiles.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* PIN Configuration Panel */}
        <div className="bg-card border border-border p-6 rounded-lg space-y-6 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-secondary rounded border border-border">
              <KeyRound className="w-4 h-4 text-primary" />
            </div>
            <div>
              <h3 className="text-sm font-bold">Secondary Lock PIN</h3>
              <p className="text-[10px] text-muted-foreground">Configure secondary validation to lock assets.</p>
            </div>
          </div>

          <form onSubmit={handlePinSubmit} className="space-y-4">
            <div className="space-y-1">
              <label className="text-[10px] font-semibold text-muted-foreground uppercase">Configure PIN (4-6 Digits)</label>
              <input
                type="password"
                maxLength={6}
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                placeholder="••••"
                className="w-full bg-background border border-border rounded px-3 py-2 text-xs focus:outline-none focus:border-primary"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-semibold text-muted-foreground uppercase">Confirm PIN</label>
              <input
                type="password"
                maxLength={6}
                value={pinConfirm}
                onChange={(e) => setPinConfirm(e.target.value)}
                placeholder="••••"
                className="w-full bg-background border border-border rounded px-3 py-2 text-xs focus:outline-none focus:border-primary"
              />
            </div>

            {pinErr && <p className="text-[10px] text-red-600 font-medium">{pinErr}</p>}
            {pinMessage && <p className="text-[10px] text-emerald-600 font-medium">{pinMessage}</p>}

            <button
              type="submit"
              className="w-full bg-primary text-primary-foreground hover:bg-primary/95 py-2.5 rounded text-xs font-semibold transition-colors"
            >
              Configure Security PIN
            </button>
          </form>
        </div>

        {/* Danger zone */}
        <div className="bg-card border border-border p-6 rounded-lg space-y-6 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-50 dark:bg-red-950/20 rounded border border-red-100 dark:border-red-900">
              <ShieldAlert className="w-4 h-4 text-red-600" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-red-600">Danger Zone</h3>
              <p className="text-[10px] text-muted-foreground">Irreversible security operations.</p>
            </div>
          </div>

          <div className="space-y-4">
            <p className="text-[11px] text-muted-foreground leading-normal">
              Wiping your document vault deletes all files from local storage, removes their vector indexes from ChromaDB, and clears relational DB tables.
            </p>
            <button
              onClick={handleWipeVault}
              className="w-full bg-red-600 hover:bg-red-700 text-white py-2.5 rounded text-xs font-semibold transition-colors"
            >
              Wipe Document Vault
            </button>
          </div>
        </div>
      </div>

      {/* Audit Log Panel */}
      <div className="bg-card border border-border p-6 rounded-lg space-y-6 shadow-sm">
        <div className="flex items-center gap-3">
          <Clock className="w-4 h-4 text-muted-foreground" />
          <h3 className="text-sm font-bold">Access Audit Log</h3>
        </div>

        {loadingLogs ? (
          <p className="text-center text-xs text-muted-foreground py-4">Fetching audit trail...</p>
        ) : auditLogs.length > 0 ? (
          <div className="overflow-x-auto border border-border rounded-lg bg-background">
            <table className="w-full text-left border-collapse text-[10px]">
              <thead>
                <tr className="bg-secondary/40 border-b border-border">
                  <th className="p-3 font-semibold text-muted-foreground uppercase">Timestamp</th>
                  <th className="p-3 font-semibold text-muted-foreground uppercase">Action</th>
                  <th className="p-3 font-semibold text-muted-foreground uppercase">Document ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-muted/35 transition-colors">
                    <td className="p-3 text-muted-foreground">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded font-semibold text-[9px] ${
                        log.action === 'DELETE' 
                          ? 'bg-red-50 text-red-800 dark:bg-red-950/20 dark:text-red-400'
                          : log.action === 'LOCK' || log.action === 'UNLOCK'
                          ? 'bg-blue-50 text-blue-800 dark:bg-blue-950/20 dark:text-blue-400'
                          : 'bg-slate-100 text-slate-800 dark:bg-slate-800/40 dark:text-slate-400'
                      }`}>
                        {log.action}
                      </span>
                    </td>
                    <td className="p-3 font-mono text-muted-foreground truncate max-w-[150px]">
                      {log.document_id || 'Global Session'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-center text-xs text-muted-foreground py-6 border border-dashed border-border rounded-lg">
            No audits recorded. Upload or lock documents to generate logs.
          </p>
        )}
      </div>
    </div>
  );
};
