import React, { useEffect, useState } from 'react';
import { useVaultStore } from '../store/useVaultStore';
import { useAuthStore } from '../store/useAuthStore';
import { 
  FileText, Lock, Unlock, Trash2, Shield, AlertCircle, X, Search, 
  List, Grid, Download, ArrowUpDown, MoreVertical, Eye
} from 'lucide-react';
import type { DocumentBrief, DocumentDetail } from '../types';

export const Vault: React.FC = () => {
  const { 
    documents, activeCategory, loading, error, 
    fetchDocuments, deleteDocument, lockDocument, unlockDocument, fetchDocumentDetail 
  } = useVaultStore();
  const { pinVerified, verifyPin } = useAuthStore();

  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [showPinModal, setShowPinModal] = useState(false);
  const [pinInput, setPinInput] = useState('');
  const [pinError, setPinError] = useState<string | null>(null);
  const [actionPendingDoc, setActionPendingDoc] = useState<DocumentBrief | null>(null);

  // Search, View Toggle, Sorting & Pagination state
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');
  const [sortField, setSortField] = useState<'name' | 'confidence' | 'date'>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const [activeMenuDocId, setActiveMenuDocId] = useState<string | null>(null);
  const itemsPerPage = 8;

  useEffect(() => {
    fetchDocuments();
    setSelectedDocId(null);
    setDetail(null);
  }, [activeCategory]);

  const handleCardClick = async (doc: DocumentBrief) => {
    if (doc.is_locked && !pinVerified) {
      setActionPendingDoc(doc);
      setPinInput('');
      setPinError(null);
      setShowPinModal(true);
      return;
    }
    
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
    fetchDocuments();
  };

  // Sort and filter logic
  const handleSort = (field: 'name' | 'confidence' | 'date') => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  // Filtered documents
  const filteredDocs = documents.filter(doc => {
    const query = searchQuery.toLowerCase();
    return (
      doc.name.toLowerCase().includes(query) ||
      (doc.document_type || '').toLowerCase().includes(query) ||
      (doc.summary || '').toLowerCase().includes(query)
    );
  });

  // Sorted documents
  const sortedDocs = [...filteredDocs].sort((a, b) => {
    let comparison = 0;
    if (sortField === 'name') {
      comparison = a.name.localeCompare(b.name);
    } else if (sortField === 'confidence') {
      comparison = a.confidence_score - b.confidence_score;
    } else if (sortField === 'date') {
      comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    }
    return sortOrder === 'asc' ? comparison : -comparison;
  });

  // Paginated documents
  const totalPages = Math.ceil(sortedDocs.length / itemsPerPage);
  const paginatedDocs = sortedDocs.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const exportCSV = () => {
    const headers = ['Name', 'Document Type', 'Confidence Score', 'Is Locked', 'Date Added'];
    const rows = sortedDocs.map(doc => [
      doc.name,
      doc.document_type || 'Unknown',
      `${Math.round(doc.confidence_score * 100)}%`,
      doc.is_locked ? 'YES' : 'NO',
      new Date(doc.created_at).toLocaleDateString()
    ]);
    const csvContent = "data:text/csv;charset=utf-8," 
      + [headers.join(','), ...rows.map(e => e.map(val => `"${val}"`).join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `neurovault_export_${activeCategory || 'all'}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex h-full relative overflow-hidden bg-[#F8FAFC] dark:bg-slate-950">
      
      {/* Document Grid / Table Panel */}
      <div className="flex-1 flex flex-col h-full min-w-0">
        
        {/* Top Header Bar */}
        <header className="h-14 border-b border-[#E5E7EB] dark:border-slate-800 bg-white dark:bg-slate-900 px-8 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2 text-xs text-[#6B7280] dark:text-slate-400">
            <span>Vault</span>
            <span>/</span>
            <span className="text-[#111827] dark:text-slate-200 font-medium">
              {activeCategory ? activeCategory : 'Universal Vault'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={exportCSV}
              className="nv-btn-secondary h-8 px-2.5"
              title="Export to CSV"
            >
              <Download className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Export</span>
            </button>
          </div>
        </header>

        {/* Toolbar Controls */}
        <div className="p-8 pb-4 shrink-0 flex flex-col md:flex-row gap-4 justify-between items-stretch md:items-center">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-[#6B7280] dark:text-slate-500 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search documents by name, type, or contents..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="nv-input pl-9"
            />
          </div>

          <div className="flex items-center gap-3">
            {/* View Mode Toggle */}
            <div className="flex border border-[#E5E7EB] dark:border-slate-800 rounded bg-white dark:bg-slate-900 p-0.5">
              <button
                onClick={() => setViewMode('table')}
                className={`p-1.5 rounded transition-all ${
                  viewMode === 'table' 
                    ? 'bg-[#F3F4F6] dark:bg-slate-800 text-[#111827] dark:text-slate-200' 
                    : 'text-[#6B7280] dark:text-slate-500 hover:text-[#111827]'
                }`}
                title="Table View"
              >
                <List className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setViewMode('grid')}
                className={`p-1.5 rounded transition-all ${
                  viewMode === 'grid' 
                    ? 'bg-[#F3F4F6] dark:bg-slate-800 text-[#111827] dark:text-slate-200' 
                    : 'text-[#6B7280] dark:text-slate-500 hover:text-[#111827]'
                }`}
                title="Grid View"
              >
                <Grid className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Core content scrolling panel */}
        <div className="flex-1 overflow-y-auto px-8 pb-8">
          {error && (
            <div className="bg-[#DC2626]/5 border border-[#DC2626]/20 text-[#DC2626] p-4 rounded mb-6 flex items-center gap-3">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span className="text-xs font-semibold">{error}</span>
            </div>
          )}

          {loading ? (
            <div className="space-y-3">
              <div className="h-8 bg-slate-200 dark:bg-slate-800 rounded animate-pulse" />
              <div className="h-12 bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 rounded animate-pulse" />
              <div className="h-12 bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 rounded animate-pulse" />
              <div className="h-12 bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 rounded animate-pulse" />
            </div>
          ) : paginatedDocs.length > 0 ? (
            viewMode === 'table' ? (
              /* Enterprise Table UI */
              <div className="nv-table-container">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr>
                      <th className="nv-th w-10">Icon</th>
                      <th className="nv-th cursor-pointer" onClick={() => handleSort('name')}>
                        <div className="flex items-center gap-1">
                          <span>Name</span>
                          <ArrowUpDown className="w-3 h-3 text-[#6B7280]" />
                        </div>
                      </th>
                      <th className="nv-th">Type</th>
                      <th className="nv-th cursor-pointer" onClick={() => handleSort('confidence')}>
                        <div className="flex items-center gap-1">
                          <span>Score</span>
                          <ArrowUpDown className="w-3 h-3 text-[#6B7280]" />
                        </div>
                      </th>
                      <th className="nv-th">Status</th>
                      <th className="nv-th cursor-pointer" onClick={() => handleSort('date')}>
                        <div className="flex items-center gap-1">
                          <span>Date Added</span>
                          <ArrowUpDown className="w-3 h-3 text-[#6B7280]" />
                        </div>
                      </th>
                      <th className="nv-th w-16 text-right pr-6">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E5E7EB] dark:divide-slate-800">
                    {paginatedDocs.map((doc) => (
                      <tr 
                        key={doc.id} 
                        className={`nv-tr-hover cursor-pointer ${selectedDocId === doc.id ? 'bg-[#EFF6FF] dark:bg-slate-800/40' : ''}`}
                        onClick={() => handleCardClick(doc)}
                      >
                        <td className="nv-td">
                          <div className="p-1.5 bg-[#F3F4F6] dark:bg-slate-800 rounded text-[#2563EB] w-8 h-8 flex items-center justify-center border border-[#E5E7EB] dark:border-slate-700">
                            <FileText className="w-4 h-4" />
                          </div>
                        </td>
                        <td className="nv-td font-medium text-[#111827] dark:text-slate-100 max-w-[200px] truncate">
                          {doc.name}
                        </td>
                        <td className="nv-td text-[#6B7280] dark:text-slate-400">
                          {doc.document_type || 'Processing...'}
                        </td>
                        <td className="nv-td font-semibold">
                          {Math.round(doc.confidence_score * 100)}%
                        </td>
                        <td className="nv-td">
                          {doc.is_locked ? (
                            <span className="nv-badge nv-badge-warning gap-1">
                              <Lock className="w-2.5 h-2.5" />
                              Locked
                            </span>
                          ) : (
                            <span className="nv-badge nv-badge-success">
                              Available
                            </span>
                          )}
                        </td>
                        <td className="nv-td text-[#6B7280] dark:text-slate-400">
                          {new Date(doc.created_at).toLocaleDateString()}
                        </td>
                        <td className="nv-td text-right pr-4" onClick={(e) => e.stopPropagation()}>
                          <div className="relative inline-block text-left">
                            <button
                              onClick={() => setActiveMenuDocId(activeMenuDocId === doc.id ? null : doc.id)}
                              className="p-1.5 hover:bg-[#F3F4F6] dark:hover:bg-slate-850 rounded text-[#6B7280] dark:text-slate-400"
                            >
                              <MoreVertical className="w-4 h-4" />
                            </button>
                            {activeMenuDocId === doc.id && (
                              <div className="absolute right-0 mt-1 w-32 bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 rounded shadow-lg z-25 text-left py-1 text-xs">
                                <button
                                  onClick={() => {
                                    handleCardClick(doc);
                                    setActiveMenuDocId(null);
                                  }}
                                  className="w-full px-3 py-2 hover:bg-[#F3F4F6] dark:hover:bg-slate-800 flex items-center gap-2 text-[#111827] dark:text-slate-200"
                                >
                                  <Eye className="w-3.5 h-3.5" />
                                  <span>View Details</span>
                                </button>
                                <button
                                  onClick={() => {
                                    toggleLock(doc);
                                    setActiveMenuDocId(null);
                                  }}
                                  className="w-full px-3 py-2 hover:bg-[#F3F4F6] dark:hover:bg-slate-800 flex items-center gap-2 text-[#111827] dark:text-slate-200"
                                >
                                  {doc.is_locked ? <Unlock className="w-3.5 h-3.5" /> : <Lock className="w-3.5 h-3.5" />}
                                  <span>{doc.is_locked ? 'Unlock' : 'Lock'}</span>
                                </button>
                                <button
                                  onClick={() => {
                                    handleDelete(doc.id);
                                    setActiveMenuDocId(null);
                                  }}
                                  className="w-full px-3 py-2 hover:bg-[#F3F4F6] dark:hover:bg-slate-800 flex items-center gap-2 text-[#DC2626]"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                  <span>Delete</span>
                                </button>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              /* Grid View */
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {paginatedDocs.map((doc) => (
                  <div
                    key={doc.id}
                    onClick={() => handleCardClick(doc)}
                    className={`bg-white dark:bg-slate-900 border p-5 rounded hover:border-[#2563EB]/40 cursor-pointer transition-all shadow-[0_1px_2px_rgba(0,0,0,0.02)] ${
                      selectedDocId === doc.id ? 'border-[#2563EB] ring-1 ring-[#2563EB]/15' : 'border-[#E5E7EB] dark:border-slate-800'
                    }`}
                  >
                    <div className="space-y-3">
                      <div className="flex items-start justify-between">
                        <div className="p-2 bg-[#F3F4F6] dark:bg-slate-800 rounded border border-[#E5E7EB] dark:border-slate-700">
                          <FileText className="w-4.5 h-4.5 text-[#2563EB]" />
                        </div>
                        {doc.is_locked && (
                          <span className="nv-badge nv-badge-warning gap-1">
                            <Lock className="w-2.5 h-2.5" />
                            Locked
                          </span>
                        )}
                      </div>

                      <div>
                        <h3 className="text-xs font-semibold text-[#111827] dark:text-slate-100 truncate">{doc.name}</h3>
                        <p className="text-[10px] text-[#6B7280] dark:text-slate-400">{doc.document_type || 'Processing Type'}</p>
                      </div>

                      {doc.summary && (
                        <p className="text-[11px] text-[#6B7280] dark:text-slate-400 line-clamp-2 leading-relaxed">
                          {doc.summary}
                        </p>
                      )}
                    </div>

                    <div className="pt-3 flex items-center justify-between border-t border-[#E5E7EB] dark:border-slate-800 mt-4 text-[10px] text-[#6B7280] dark:text-slate-500 font-medium">
                      <span>Score: {Math.round(doc.confidence_score * 100)}%</span>
                      <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            <div className="py-20 text-center border border-dashed border-[#E5E7EB] dark:border-slate-800 rounded text-xs text-[#6B7280] space-y-1">
              <p className="font-semibold">No records found.</p>
              <p className="text-[11px]">Upload credentials or identity cards to populate the archive.</p>
            </div>
          )}

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-6 border-t border-[#E5E7EB] dark:border-slate-800 mt-6">
              <span className="text-[11px] text-[#6B7280] dark:text-slate-400">
                Showing {Math.min(filteredDocs.length, (currentPage - 1) * itemsPerPage + 1)}-{Math.min(filteredDocs.length, currentPage * itemsPerPage)} of {filteredDocs.length} items
              </span>
              <div className="flex gap-2">
                <button
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  className="nv-btn-secondary h-8 px-3"
                >
                  Previous
                </button>
                <button
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  className="nv-btn-secondary h-8 px-3"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Slide-over Detail Sidebar Panel */}
      {detail && (
        <div className="w-[380px] border-l border-[#E5E7EB] dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col h-full shadow-lg relative shrink-0">
          <div className="h-14 px-6 border-b border-[#E5E7EB] dark:border-slate-800 flex items-center justify-between shrink-0">
            <div className="space-y-0.5 max-w-[200px]">
              <h2 className="text-xs font-semibold text-[#111827] dark:text-slate-100 truncate">{detail.name}</h2>
              <p className="text-[10px] text-[#6B7280] dark:text-slate-400">{detail.document_type}</p>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => toggleLock(detail)}
                className="p-1.5 hover:bg-[#F3F4F6] dark:hover:bg-slate-800 rounded text-[#6B7280] dark:text-slate-400 hover:text-[#111827]"
                title={detail.is_locked ? 'Unlock document' : 'PIN Lock Document'}
              >
                {detail.is_locked ? <Lock className="w-4 h-4 text-[#2563EB]" /> : <Unlock className="w-4 h-4" />}
              </button>
              <button
                onClick={() => handleDelete(detail.id)}
                className="p-1.5 hover:bg-[#DC2626]/5 hover:text-[#DC2626] rounded text-[#6B7280] dark:text-slate-400"
                title="Delete document"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setDetail(null)}
                className="p-1.5 hover:bg-[#F3F4F6] dark:hover:bg-slate-800 rounded text-[#6B7280] dark:text-slate-400"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="p-6 space-y-6 flex-1 overflow-y-auto">
            {/* Format info badges */}
            <div className="grid grid-cols-2 gap-4 border-b border-[#E5E7EB] dark:border-slate-850 pb-4">
              <div>
                <p className="text-[10px] font-bold text-[#6B7280] dark:text-slate-500 uppercase tracking-wider">Format</p>
                <p className="font-semibold text-xs text-[#111827] dark:text-slate-200 uppercase mt-0.5">{detail.file_type}</p>
              </div>
              <div>
                <p className="text-[10px] font-bold text-[#6B7280] dark:text-slate-500 uppercase tracking-wider">OCR Confidence</p>
                <p className="font-semibold text-xs text-[#111827] dark:text-slate-200 mt-0.5">{Math.round(detail.confidence_score * 100)}%</p>
              </div>
            </div>

            {/* Smart Tags */}
            {detail.tags.length > 0 && (
              <div className="space-y-2">
                <p className="text-[10px] font-bold text-[#6B7280] dark:text-slate-500 uppercase tracking-wider">Metadata Tags</p>
                <div className="flex flex-wrap gap-1.5">
                  {detail.tags.map((t) => (
                    <span key={t.id} className="nv-badge nv-badge-neutral">
                      {t.tag_name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Summary details */}
            <div className="space-y-2">
              <p className="text-[10px] font-bold text-[#6B7280] dark:text-slate-500 uppercase tracking-wider">Summary Card</p>
              <div className="bg-[#F8FAFC] dark:bg-slate-950/40 border border-[#E5E7EB] dark:border-slate-800 p-3.5 rounded text-xs text-[#6B7280] dark:text-slate-300 leading-relaxed shadow-[inset_0_1px_1px_rgba(0,0,0,0.01)]">
                {detail.summary}
              </div>
            </div>

            {/* Extracted JSON fields */}
            <div className="space-y-2">
              <p className="text-[10px] font-bold text-[#6B7280] dark:text-slate-500 uppercase tracking-wider">Parsed Structured Fields</p>
              <div className="border border-[#E5E7EB] dark:border-slate-800 rounded bg-[#F8FAFC] dark:bg-slate-950/40 p-3 text-xs max-h-72 overflow-y-auto">
                {typeof detail.extracted_json === 'object' && detail.extracted_json !== null ? (
                  Object.keys(detail.extracted_json).map((key) => {
                    const val = detail.extracted_json[key];
                    let displayVal = '';
                    
                    if (typeof val === 'object') {
                      displayVal = JSON.stringify(val);
                    } else {
                      displayVal = String(val);
                    }
                    
                    // Masking logic
                    if (key.includes('number') || key.includes('no') || key.includes('id') || key.includes('aadhaar') || key.includes('pan')) {
                      if (displayVal.length === 12 && /^\d+$/.test(displayVal)) {
                        displayVal = `XXXX-XXXX-${displayVal.substring(8)}`;
                      } else if (displayVal.length === 10 && /^[A-Z]{5}\d{4}[A-Z]/.test(displayVal)) {
                        displayVal = `${displayVal.substring(0, 5)}****${displayVal.substring(9)}`;
                      } else if (displayVal.length > 8) {
                        displayVal = `XXXX-${displayVal.substring(displayVal.length - 4)}`;
                      }
                    }

                    return (
                      <div key={key} className="py-2 border-b border-[#E5E7EB]/60 dark:border-slate-800/60 last:border-0 flex justify-between gap-4">
                        <span className="font-semibold text-[#111827] dark:text-slate-300 shrink-0">{key}:</span>
                        <span className="text-right text-[#6B7280] dark:text-slate-400 break-all">{displayVal}</span>
                      </div>
                    );
                  })
                ) : (
                  <pre className="font-mono text-[10px] text-[#6B7280]">{JSON.stringify(detail.extracted_json, null, 2)}</pre>
                )}
              </div>
            </div>

          </div>
        </div>
      )}

      {/* Security PIN verification modal */}
      {showPinModal && (
        <div className="absolute inset-0 bg-slate-950/40 dark:bg-slate-950/80 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-850 rounded max-w-sm w-full p-6 space-y-6 shadow-xl">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-[#2563EB]/5 rounded border border-[#2563EB]/15 text-[#2563EB]">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-xs font-semibold text-[#111827] dark:text-slate-100">Verify Security PIN</h3>
                <p className="text-[11px] text-[#6B7280] dark:text-slate-400">Enter secondary PIN to decrypt locked credential layers.</p>
              </div>
            </div>

            <form onSubmit={handlePinSubmit} className="space-y-4">
              <input
                type="password"
                maxLength={6}
                value={pinInput}
                onChange={(e) => setPinInput(e.target.value)}
                placeholder="••••••"
                className="w-full text-center tracking-[1em] font-mono border border-[#E5E7EB] dark:border-slate-800 rounded px-3 py-2 text-sm bg-white dark:bg-slate-950 text-[#111827] dark:text-slate-100 focus:outline-none focus:border-[#2563EB]"
                autoFocus
              />
              {pinError && <p className="text-[10px] text-[#DC2626] text-center font-medium">{pinError}</p>}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowPinModal(false)}
                  className="flex-1 nv-btn-secondary h-9"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 nv-btn-primary h-9"
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
