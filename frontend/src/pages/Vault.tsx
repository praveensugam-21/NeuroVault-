import React, { useEffect, useState } from 'react';
import { useVaultStore } from '../store/useVaultStore';
import { useAuthStore } from '../store/useAuthStore';
import { FileText, Lock, Unlock, Trash2, Shield, AlertCircle, X } from 'lucide-react';
import type { DocumentBrief, DocumentDetail } from '../types';

export const Vault: React.FC = () => {
  const { documents, activeCategory, loading, error, fetchDocuments, deleteDocument, lockDocument, unlockDocument, fetchDocumentDetail } = useVaultStore();
  const { pinVerified, verifyPin } = useAuthStore();

  
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [showPinModal, setShowPinModal] = useState(false);
  const [pinInput, setPinInput] = useState('');
  const [pinError, setPinError] = useState<string | null>(null);
  const [actionPendingDoc, setActionPendingDoc] = useState<DocumentBrief | null>(null);

  useEffect(() => {
    fetchDocuments();
  }, [activeCategory]);

  const handleCardClick = async (doc: DocumentBrief) => {
    if (doc.is_locked && !pinVerified) {
      setActionPendingDoc(doc);
      setPinInput('');
      setPinError(null);
      setShowPinModal(true);
      return;
    }
    
    // Retrieve details
    await loadDocDetail(doc.id);
  };

  const loadDocDetail = async (id: string, pinCode?: string) => {
    const data = await fetchDocumentDetail(id, pinCode);
    if (data) {
      setDetail(data);
      setSelectedDocId(id);
    }
  };

  const handlePinSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPinError(null);
    if (!actionPendingDoc) return;

    try {
      const success = await verifyPin(pinInput);
      if (success) {
        setShowPinModal(false);
        await loadDocDetail(actionPendingDoc.id, pinInput);
      } else {
        setPinError('Incorrect security PIN.');
      }
    } catch (err) {
      setPinError('Incorrect security PIN.');
    }
  };

  const handleDelete = async (id: string) => {
    if (window.confirm('Are you sure you want to permanently delete this document and all its semantic memories?')) {
      const success = await deleteDocument(id);
      if (success && selectedDocId === id) {
        setSelectedDocId(null);
        setDetail(null);
      }
    }
  };

  const toggleLock = async (doc: DocumentBrief) => {
    if (doc.is_locked) {
      const success = await unlockDocument(doc.id);
      if (success && detail && detail.id === doc.id) {
        setDetail({ ...detail, is_locked: false });
      }
    } else {
      const success = await lockDocument(doc.id);
      if (success && detail && detail.id === doc.id) {
        setDetail({ ...detail, is_locked: true });
      }
    }
  };

  return (
    <div className="flex h-full relative overflow-hidden">
      {/* Document Grid Panel */}
      <div className="flex-1 p-8 overflow-y-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {activeCategory ? activeCategory : 'Universal Vault'}
          </h1>
          <p className="text-muted-foreground text-sm">
            Browse structured memories parsed across all folders.
          </p>
        </div>

        {error && (
          <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900 text-red-800 dark:text-red-400 p-4 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="text-xs">{error}</span>
          </div>
        )}

        {loading ? (
          <div className="py-20 text-center text-xs text-muted-foreground">
            Searching vault memories...
          </div>
        ) : documents.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {documents.map((doc) => (
              <div
                key={doc.id}
                onClick={() => handleCardClick(doc)}
                className={`bg-card border p-5 rounded-lg flex flex-col justify-between hover:border-primary/50 cursor-pointer transition-all shadow-sm ${
                  selectedDocId === doc.id ? 'border-primary ring-1 ring-primary/20' : 'border-border'
                }`}
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="p-2 bg-secondary rounded border border-border">
                      <FileText className="w-4 h-4 text-primary" />
                    </div>
                    {doc.is_locked && (
                      <span className="flex items-center gap-1 text-[10px] text-primary bg-primary/10 px-2 py-0.5 rounded font-semibold">
                        <Lock className="w-3 h-3" />
                        Locked
                      </span>
                    )}
                  </div>

                  <div>
                    <h3 className="text-sm font-bold truncate">{doc.name}</h3>
                    <p className="text-[11px] text-muted-foreground">{doc.document_type || 'Processing Type'}</p>
                  </div>

                  {doc.summary && (
                    <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                      {doc.summary}
                    </p>
                  )}
                </div>

                <div className="pt-4 flex items-center justify-between border-t border-border mt-4 text-[10px] text-muted-foreground">
                  <span>Score: {Math.round(doc.confidence_score * 100)}%</span>
                  <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-24 text-center border border-dashed border-border rounded-lg text-xs text-muted-foreground space-y-2">
            <p>No documents found in this folder.</p>
            <p className="text-[11px]">Upload images or PDFs to see auto-categorization in action.</p>
          </div>
        )}
      </div>

      {/* Slide-over Detail Modal Panel */}
      {detail && (
        <div className="w-96 border-l border-border bg-card flex flex-col h-full shadow-lg relative">
          <div className="p-6 border-b border-border flex items-center justify-between">
            <div className="space-y-0.5">
              <h2 className="text-sm font-bold truncate max-w-[200px]">{detail.name}</h2>
              <p className="text-[10px] text-muted-foreground">{detail.document_type}</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => toggleLock(detail)}
                className="p-1.5 hover:bg-muted rounded text-muted-foreground hover:text-foreground"
                title={detail.is_locked ? 'Unlock document' : 'PIN Lock Document'}
              >
                {detail.is_locked ? <Lock className="w-4 h-4 text-primary" /> : <Unlock className="w-4 h-4" />}
              </button>
              <button
                onClick={() => handleDelete(detail.id)}
                className="p-1.5 hover:bg-red-50 hover:text-red-600 rounded text-muted-foreground"
                title="Delete document"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setDetail(null)}
                className="p-1.5 hover:bg-muted rounded text-muted-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="p-6 space-y-6 flex-1 overflow-y-auto">
            {/* Info Badges */}
            <div className="flex items-center gap-4 text-xs">
              <div>
                <p className="text-[10px] text-muted-foreground uppercase">Format</p>
                <p className="font-semibold uppercase">{detail.file_type}</p>
              </div>
              <div className="w-px h-8 bg-border" />
              <div>
                <p className="text-[10px] text-muted-foreground uppercase">OCR Match</p>
                <p className="font-semibold">{Math.round(detail.confidence_score * 100)}%</p>
              </div>
            </div>

            {/* Tags */}
            {detail.tags.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-[10px] text-muted-foreground uppercase">Smart Tags</p>
                <div className="flex flex-wrap gap-1.5">
                  {detail.tags.map((t) => (
                    <span key={t.id} className="text-[10px] bg-secondary border border-border px-2 py-0.5 rounded text-foreground font-medium">
                      {t.tag_name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Summary card */}
            <div className="space-y-1.5">
              <p className="text-[10px] text-muted-foreground uppercase">Summary Card</p>
              <div className="bg-secondary/30 border border-border p-3 rounded-lg text-xs leading-relaxed text-muted-foreground">
                {detail.summary}
              </div>
            </div>

            {/* Extracted Fields JSON Schema */}
            <div className="space-y-1.5 flex-1">
              <p className="text-[10px] text-muted-foreground uppercase">Extracted Structured Fields</p>
              <div className="border border-border rounded-lg bg-background p-3 overflow-x-auto text-[11px] font-mono text-muted-foreground max-h-72">
                {typeof detail.extracted_json === 'object' ? (
                  Object.keys(detail.extracted_json).map((key) => {
                    const val = detail.extracted_json[key];
                    let displayVal = '';
                    
                    // Display formatting
                    if (typeof val === 'object') {
                      displayVal = JSON.stringify(val);
                    } else {
                      displayVal = String(val);
                    }
                    
                    // Professional Masking visual representation for display
                    if (key.includes('number') || key.includes('no') || key.includes('id') || key.includes('aadhaar') || key.includes('pan')) {
                      if (displayVal.length === 12 && /^\d+$/.test(displayVal)) {
                        // Aadhaar Mask
                        displayVal = `XXXX-XXXX-${displayVal.substring(8)}`;
                      } else if (displayVal.length === 10 && /^[A-Z]{5}\d{4}[A-Z]/.test(displayVal)) {
                        // PAN Mask
                        displayVal = `${displayVal.substring(0, 5)}****${displayVal.substring(9)}`;
                      } else if (displayVal.length > 8) {
                        displayVal = `XXXX-${displayVal.substring(displayVal.length - 4)}`;
                      }
                    }

                    return (
                      <div key={key} className="py-1 border-b border-border/50 last:border-0 flex items-start justify-between gap-4">
                        <span className="font-semibold text-foreground shrink-0">{key}:</span>
                        <span className="text-right break-all">{displayVal}</span>
                      </div>
                    );
                  })
                ) : (
                  <pre>{JSON.stringify(detail.extracted_json, null, 2)}</pre>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Security PIN verification modal */}
      {showPinModal && (
        <div className="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg max-w-sm w-full p-6 space-y-6 shadow-xl">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded">
                <Shield className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="text-sm font-bold">Verify Security PIN</h3>
                <p className="text-[11px] text-muted-foreground">Enter your 4-6 digit account PIN to access locked assets.</p>
              </div>
            </div>

            <form onSubmit={handlePinSubmit} className="space-y-4">
              <input
                type="password"
                maxLength={6}
                value={pinInput}
                onChange={(e) => setPinInput(e.target.value)}
                placeholder="••••••"
                className="w-full text-center tracking-[1.2em] font-mono border border-border rounded px-3 py-2 text-sm bg-background focus:outline-none focus:border-primary"
                autoFocus
              />
              {pinError && <p className="text-[10px] text-red-600 text-center font-medium">{pinError}</p>}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowPinModal(false)}
                  className="flex-1 border border-border hover:bg-muted text-xs font-semibold py-2 rounded transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 bg-primary text-primary-foreground hover:bg-primary/95 text-xs font-semibold py-2 rounded transition-colors"
                >
                  Verify
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
