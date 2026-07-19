import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../store/useAuthStore';
import { useVaultStore } from '../store/useVaultStore';
import { KeyRound, Clock, ShieldAlert, Check, Cpu } from 'lucide-react';
import api from '../services/api';

type SettingsTab = 'security' | 'audit' | 'ai';

export const Settings: React.FC = () => {
  const { setupPin, error, clearError } = useAuthStore();
  const { fetchDocuments, fetchStats } = useVaultStore();

  const [activeTab, setActiveTab] = useState<SettingsTab>('security');
  const [pin, setPin] = useState('');
  const [pinConfirm, setPinConfirm] = useState('');
  const [pinMessage, setPinMessage] = useState<string | null>(null);
  const [pinErr, setPinErr] = useState<string | null>(null);
  
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  // AI Configuration states
  const [geminiKey, setGeminiKey] = useState('');
  const [ollamaUrl, setOllamaUrl] = useState('');
  const [aiMessage, setAiMessage] = useState<string | null>(null);
  const [aiErr, setAiErr] = useState<string | null>(null);
  const [loadingAiConfig, setLoadingAiConfig] = useState(false);
  const [savingAiConfig, setSavingAiConfig] = useState(false);

  useEffect(() => {
    fetchAuditLogs();
    clearError();
  }, []);

  useEffect(() => {
    if (activeTab === 'ai') {
      fetchAiConfig();
    }
  }, [activeTab]);

  const fetchAiConfig = async () => {
    setLoadingAiConfig(true);
    setAiErr(null);
    try {
      const response = await api.get('/api/auth/ai-config');
      setGeminiKey(response.data.gemini_api_key || '');
      setOllamaUrl(response.data.ollama_base_url || '');
    } catch (err: any) {
      console.error(err);
      setAiErr(err.response?.data?.detail || 'Failed to load AI configuration.');
    } finally {
      setLoadingAiConfig(false);
    }
  };

  const handleAiConfigSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAiErr(null);
    setAiMessage(null);
    setSavingAiConfig(true);
    try {
      await api.post('/api/auth/ai-config', {
        gemini_api_key: geminiKey,
        ollama_base_url: ollamaUrl
      });
      setAiMessage('AI settings updated successfully.');
      await fetchAiConfig();
    } catch (err: any) {
      console.error(err);
      setAiErr(err.response?.data?.detail || 'Failed to save AI configuration.');
    } finally {
      setSavingAiConfig(false);
    }
  };

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
        await api.delete('/api/documents/');
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
    <div className="flex flex-col h-full bg-[#F8FAFC] dark:bg-slate-950 overflow-y-auto">
      
      {/* Top Header Bar */}
      <header className="h-14 border-b border-[#E5E7EB] dark:border-slate-800 bg-white dark:bg-slate-900 px-8 flex items-center shrink-0">
        <div className="flex items-center gap-2 text-xs text-[#6B7280]">
          <span>System</span>
          <span>/</span>
          <span className="text-[#111827] dark:text-slate-200 font-medium">Security & Settings</span>
        </div>
      </header>
 
      {/* Settings Layout Tab Rail Split */}
      <div className="p-8 max-w-6xl w-full mx-auto space-y-8 flex-1 flex flex-col md:flex-row items-start gap-8">
        
        {/* Left Sub-Tab Navigation Rail */}
        <div className="w-full md:w-48 shrink-0 flex flex-col gap-1 select-none">
          <button
            onClick={() => setActiveTab('security')}
            className={`w-full text-left px-3 py-2 rounded text-xs font-semibold transition-all ${
              activeTab === 'security'
                ? 'bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 text-[#2563EB]'
                : 'text-[#6B7280] dark:text-slate-400 hover:bg-[#F3F4F6] hover:text-[#111827]'
            }`}
          >
            Security & Controls
          </button>
          <button
            onClick={() => setActiveTab('ai')}
            className={`w-full text-left px-3 py-2 rounded text-xs font-semibold transition-all ${
              activeTab === 'ai'
                ? 'bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 text-[#2563EB]'
                : 'text-[#6B7280] dark:text-slate-400 hover:bg-[#F3F4F6] hover:text-[#111827]'
            }`}
          >
            AI Configuration
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`w-full text-left px-3 py-2 rounded text-xs font-semibold transition-all ${
              activeTab === 'audit'
                ? 'bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 text-[#2563EB]'
                : 'text-[#6B7280] dark:text-slate-400 hover:bg-[#F3F4F6] hover:text-[#111827]'
            }`}
          >
            Access Audit Trail
          </button>
        </div>

        {/* Right Active Tab Content Panels */}
        <div className="flex-1 w-full space-y-8">
          
          {activeTab === 'security' && (
            <div className="space-y-8">
              {/* PIN Settings Card */}
              <div className="bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 p-6 rounded shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-[#F3F4F6] dark:bg-slate-800 rounded border border-[#E5E7EB] dark:border-slate-700 text-[#6B7280]">
                    <KeyRound className="w-4 h-4 text-[#2563EB]" />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-[#111827] dark:text-slate-200">Secondary Security PIN</h3>
                    <p className="text-[11px] text-[#6B7280] dark:text-slate-400">Configure secondary lock layer credentials to encrypt vaults.</p>
                  </div>
                </div>

                <form onSubmit={handlePinSubmit} className="space-y-4 max-w-sm">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-[#6B7280] dark:text-slate-400 uppercase tracking-wider">
                      New PIN (4-6 Digits)
                    </label>
                    <input
                      type="password"
                      maxLength={6}
                      value={pin}
                      onChange={(e) => setPin(e.target.value)}
                      placeholder="••••"
                      className="nv-input"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-[#6B7280] dark:text-slate-400 uppercase tracking-wider">
                      Confirm Security PIN
                    </label>
                    <input
                      type="password"
                      maxLength={6}
                      value={pinConfirm}
                      onChange={(e) => setPinConfirm(e.target.value)}
                      placeholder="••••"
                      className="nv-input"
                    />
                  </div>

                  {pinErr && <p className="text-[10px] text-[#DC2626] font-medium">{pinErr}</p>}
                  {pinMessage && (
                    <p className="text-[10px] text-[#16A34A] font-medium flex items-center gap-1.5">
                      <Check className="w-3.5 h-3.5" />
                      <span>{pinMessage}</span>
                    </p>
                  )}

                  <button
                    type="submit"
                    className="nv-btn-primary h-9 w-full font-semibold"
                  >
                    Setup Security PIN
                  </button>
                </form>
              </div>

              {/* Danger Zone Card */}
              <div className="bg-white dark:bg-slate-900 border border-[#DC2626]/20 p-6 rounded shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-[#DC2626]/5 rounded border border-[#DC2626]/10 text-[#DC2626]">
                    <ShieldAlert className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-[#DC2626]">System Danger Operations</h3>
                    <p className="text-[11px] text-[#6B7280]">Irreversible master vault data deletions.</p>
                  </div>
                </div>

                <div className="space-y-4 max-w-lg">
                  <p className="text-[11px] text-[#6B7280] leading-relaxed">
                    Executing a vault wipe command permanently deletes all relational files from storage pools, clears your ChromaDB vector index stores, and removes metadata nodes. This cannot be undone.
                  </p>
                  <button
                    onClick={handleWipeVault}
                    className="nv-btn-danger font-semibold h-9"
                  >
                    Wipe Document Vault
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'audit' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-[#F3F4F6] dark:bg-slate-800 rounded border border-[#E5E7EB] dark:border-slate-700 text-[#6B7280]">
                  <Clock className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-[#111827] dark:text-slate-200">Access Audit Trail</h3>
                  <p className="text-[11px] text-[#6B7280]">History log of document lock updates and delete transactions.</p>
                </div>
              </div>

              {loadingLogs ? (
                <p className="text-center text-xs text-[#6B7280] py-12">Fetching secure audit trail logs...</p>
              ) : auditLogs.length > 0 ? (
                <div className="nv-table-container">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr>
                        <th className="nv-th">Timestamp</th>
                        <th className="nv-th">Action Executed</th>
                        <th className="nv-th">Document Target Identifier</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E5E7EB] dark:divide-slate-800">
                      {auditLogs.map((log) => (
                        <tr key={log.id} className="nv-tr-hover">
                          <td className="nv-td text-[#6B7280]">
                            {new Date(log.timestamp).toLocaleString()}
                          </td>
                          <td className="nv-td">
                            <span className={`nv-badge ${
                              log.action === 'DELETE' 
                                ? 'nv-badge-danger'
                                : log.action === 'LOCK' || log.action === 'UNLOCK'
                                ? 'nv-badge-success'
                                : 'nv-badge-neutral'
                            }`}>
                              {log.action}
                            </span>
                          </td>
                          <td className="nv-td font-mono text-[10px] text-[#6B7280] truncate max-w-[200px]">
                            {log.document_id || 'System Console Session'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-center text-xs text-[#6B7280] py-16 border border-dashed border-[#E5E7EB] dark:border-slate-800 rounded">
                  No audits recorded. Lock documents to generate audit rows.
                </p>
              )}
            </div>
          )}

          {activeTab === 'ai' && (
            <div className="space-y-6">
              <div className="bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 p-6 rounded shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-[#F3F4F6] dark:bg-slate-800 rounded border border-[#E5E7EB] dark:border-slate-700 text-[#6B7280]">
                    <Cpu className="w-4 h-4 text-[#2563EB]" />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-[#111827] dark:text-slate-200">AI Model Configuration</h3>
                    <p className="text-[11px] text-[#6B7280] dark:text-slate-400">Configure online/offline LLM backends to power RAG chat assistant queries.</p>
                  </div>
                </div>

                {loadingAiConfig ? (
                  <p className="text-xs text-[#6B7280] py-4">Fetching active configuration...</p>
                ) : (
                  <form onSubmit={handleAiConfigSubmit} className="space-y-5 max-w-lg">
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold text-[#6B7280] dark:text-slate-400 uppercase tracking-wider">
                        Gemini API Key (Google AI Studio)
                      </label>
                      <input
                        type="password"
                        value={geminiKey}
                        onChange={(e) => setGeminiKey(e.target.value)}
                        placeholder={geminiKey ? "••••••••••••••••" : "Paste your Google AI Studio API key here"}
                        className="nv-input w-full"
                      />
                      <p className="text-[10px] text-[#6B7280] dark:text-slate-500">
                        Recommended. Powered by Gemini 2.5 Flash. Direct vault context grounding, zero hallucination. Supports general-knowledge queries.
                      </p>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold text-[#6B7280] dark:text-slate-400 uppercase tracking-wider">
                        Ollama Base URL (Offline Fallback)
                      </label>
                      <input
                        type="text"
                        value={ollamaUrl}
                        onChange={(e) => setOllamaUrl(e.target.value)}
                        placeholder="e.g. http://localhost:11434"
                        className="nv-input w-full font-mono text-xs"
                      />
                      <p className="text-[10px] text-[#6B7280] dark:text-slate-500">
                        Offline fallback server URL. Set to "disabled" to prevent local Ollama checks.
                      </p>
                    </div>

                    {aiErr && <p className="text-[10px] text-[#DC2626] font-medium">{aiErr}</p>}
                    {aiMessage && (
                      <p className="text-[10px] text-[#16A34A] font-medium flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5" />
                        <span>{aiMessage}</span>
                      </p>
                    )}

                    <button
                      type="submit"
                      disabled={savingAiConfig}
                      className="nv-btn-primary h-9 font-semibold px-4 flex items-center justify-center gap-2"
                    >
                      {savingAiConfig ? 'Saving Settings...' : 'Save AI Configuration'}
                    </button>
                  </form>
                )}
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};
