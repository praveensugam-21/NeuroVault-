import React, { useState } from 'react';
import { useVaultStore } from '../store/useVaultStore';
import { CheckCircle2, AlertCircle, FileUp, Loader2 } from 'lucide-react';
import api from '../services/api';

interface PipelineStep {
  label: string;
  desc: string;
}

export const Upload: React.FC = () => {
  const { fetchDocuments, fetchStats } = useVaultStore();

  const [file, setFile] = useState<File | null>(null);
  const [customName, setCustomName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [pipelineActive, setPipelineActive] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(-1);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const pipelineSteps: PipelineStep[] = [
    { label: 'File Upload & Verification', desc: 'Validating checksum payloads and verifying MIME-headers.' },
    { label: 'OpenCV Image Enhancements', desc: 'Executing contrast stretch, blur filters, and tilt de-skewing.' },
    { label: 'OCR & Text Processing', desc: 'Running local OCR parser to extract raw textual lines.' },
    { label: 'Document Classification', desc: 'Comparing document headers against our taxonomy classifier rules.' },
    { label: 'JSON Fields Extraction', desc: 'Building custom metadata fields using RAG target formats.' },
    { label: 'Integrity Field Checks', desc: 'Cross-verifying date strings, identities, and unique identification structures.' },
    { label: 'Character Integrity Checks', desc: 'Analyzing OCR extraction certainty metrics across fields.' },
    { label: 'Automated Summary Card', desc: 'Writing a natural-language description mapping key variables.' },
    { label: 'Named Entity Routing (NER)', desc: 'Detecting references to locations, entities, and specific dates.' },
    { label: '384-Dim Vector Computation', desc: 'Running local sentence transformer models to embed metadata indexes.' },
    { label: 'ChromaDB Core Indexing', desc: 'Saving generated semantic embeddings to local database pools.' },
    { label: 'Knowledge Graph Linking', desc: 'Running proximity searches to connect documents with matches.' },
    { label: 'Expiration Parser Check', desc: 'Checking expiry strings and payment schedules for alerts.' },
    { label: 'Smart Folder Archiving', desc: 'Routing the document to designated folders and tagging tags.' },
    { label: 'Final SQLite Archiving', desc: 'Updating record database schemas and refreshing dashboard logs.' }
  ];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setCustomName(e.target.files[0].name.split('.')[0]);
      setError(null);
      setSuccess(false);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setError(null);
    setSuccess(false);
    setUploading(true);
    setPipelineActive(true);
    setCurrentStepIndex(0);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', customName || file.name.split('.')[0]);

    try {
      const response = await api.post('/api/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const docId = response.data.document_id;

      // Start responsive layout progress stepper increment
      let stepIndex = 0;
      const progressInterval = setInterval(() => {
        if (stepIndex < 13) { // Cap at step 14 ("Auto-Tagging & Folder Routing")
          stepIndex++;
          setCurrentStepIndex(stepIndex);
        }
      }, 200);

      // Poll backend status until complete or failed
      let completed = false;
      while (!completed) {
        await new Promise((resolve) => setTimeout(resolve, 800)); // Poll every 800ms
        
        try {
          const checkResponse = await api.get(`/api/documents/${docId}`);
          const status = checkResponse.data.status;
          
          if (status === 'COMPLETE' || status === 'FAILED') {
            completed = true;
            clearInterval(progressInterval);
            
            if (status === 'FAILED') {
              throw new Error('Pipeline processing failed.');
            }
            
            // Fast-forward progress steps to completion instantly
            setCurrentStepIndex(pipelineSteps.length - 1);
            setSuccess(true);
          }
        } catch (pollErr: any) {
          completed = true;
          clearInterval(progressInterval);
          throw new Error(pollErr.message || pollErr.response?.data?.detail || 'Verification check failed.');
        }
      }

      await fetchDocuments();
      await fetchStats();
      setFile(null);
      setCustomName('');
    } catch (err: any) {
      setError(err.message || err.response?.data?.detail || 'Failed to complete document upload pipeline.');
      setPipelineActive(false);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#F8FAFC] dark:bg-slate-950 overflow-y-auto">
      
      {/* Top Header Bar */}
      <header className="h-14 border-b border-[#E5E7EB] dark:border-slate-800 bg-white dark:bg-slate-900 px-8 flex items-center shrink-0">
        <div className="flex items-center gap-2 text-xs text-[#6B7280]">
          <span>Upload</span>
          <span>/</span>
          <span className="text-[#111827] dark:text-slate-200 font-medium">Upload Center</span>
        </div>
      </header>

      {/* Main Container (Centered and Minimal width) */}
      <div className="p-8 max-w-2xl w-full mx-auto space-y-8 flex-1">
        
        {/* Title */}
        <div>
          <h1 className="text-24px font-semibold text-[#111827] dark:text-slate-100 tracking-tight">Upload Center</h1>
          <p className="text-xs text-[#6B7280] dark:text-slate-400 mt-1">
            Submit credentials to run the 15-stage semantic ingestion and classification pipeline.
          </p>
        </div>

        <div className="space-y-6">
          {/* Upload Form Card */}
          <div className="bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 p-6 rounded shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-6">
            <h2 className="text-xs font-bold uppercase tracking-wider text-[#6B7280] dark:text-slate-400">Select File</h2>
            
            <form onSubmit={handleUploadSubmit} className="space-y-6">
              {/* Drag drop zone */}
              <div className="border border-dashed border-[#E5E7EB] dark:border-slate-800 rounded bg-[#F8FAFC] dark:bg-slate-950/40 p-8 hover:bg-white hover:border-[#2563EB]/40 transition-all text-center relative group cursor-pointer">
                <input
                  type="file"
                  onChange={handleFileChange}
                  accept=".pdf,.png,.jpg,.jpeg,.mp3,.wav,.m4a,.txt"
                  className="absolute inset-0 opacity-0 cursor-pointer"
                  disabled={uploading}
                />
                <div className="flex flex-col items-center justify-center gap-3 select-none">
                  <FileUp className="w-6 h-6 text-[#6B7280] group-hover:text-[#2563EB] transition-colors" />
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-[#111827] dark:text-slate-200">{file ? file.name : 'Click to select file'}</p>
                    <p className="text-[10px] text-[#6B7280]">
                      PDF, PNG, JPG, MP3, WAV, TXT up to 10MB
                    </p>
                  </div>
                </div>
              </div>

              {/* Display Name Input */}
              {file && (
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-[#6B7280] dark:text-slate-400 uppercase tracking-wider">
                    Document Display Name
                  </label>
                  <input
                    type="text"
                    value={customName}
                    onChange={(e) => setCustomName(e.target.value)}
                    placeholder="Enter custom document name"
                    className="nv-input"
                    disabled={uploading}
                  />
                </div>
              )}

              {error && (
                <div className="bg-[#DC2626]/5 border border-[#DC2626]/20 text-[#DC2626] p-3 rounded text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span className="font-medium">{error}</span>
                </div>
              )}

              {success && (
                <div className="bg-[#16A34A]/5 border border-[#16A34A]/20 text-[#16A34A] p-3 rounded text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  <span className="font-medium">File uploaded, analyzed, and linked successfully!</span>
                </div>
              )}

              <button
                type="submit"
                disabled={!file || uploading}
                className="w-full nv-btn-primary h-10 font-semibold"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Running Ingestion...</span>
                  </>
                ) : (
                  'Process Ingestion Pipeline'
                )}
              </button>
            </form>
          </div>

          {/* Stepper progression section (now stacked below the form card) */}
          {pipelineActive && (
            <div className="bg-white dark:bg-slate-900 border border-[#E5E7EB] dark:border-slate-800 p-6 rounded shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-6">
              <div className="flex items-center justify-between border-b border-[#E5E7EB] dark:border-slate-800 pb-3">
                <h2 className="text-xs font-bold uppercase tracking-wider text-[#6B7280]">Pipeline Progression</h2>
                <span className="text-[10px] text-[#2563EB] font-bold">
                  Step {currentStepIndex + 1} of {pipelineSteps.length}
                </span>
              </div>
              
              <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                {pipelineSteps.map((step, idx) => {
                  const isCompleted = idx < currentStepIndex;
                  const isActive = idx === currentStepIndex;

                  let borderClass = 'border-[#E5E7EB] dark:border-slate-800';
                  let bgClass = 'bg-white dark:bg-slate-900';
                  let titleClass = 'text-[#6B7280] dark:text-slate-500';

                  if (isCompleted) {
                    borderClass = 'border-[#2563EB]/15';
                    bgClass = 'bg-[#2563EB]/5';
                    titleClass = 'text-[#6B7280] dark:text-slate-350';
                  } else if (isActive) {
                    borderClass = 'border-[#2563EB]';
                    bgClass = 'bg-[#2563EB]/10';
                    titleClass = 'text-[#2563EB] font-bold';
                  }

                  return (
                    <div 
                      key={idx} 
                      className={`flex items-start gap-3 p-3 border rounded transition-all ${borderClass} ${bgClass}`}
                    >
                      <div className="mt-0.5 flex-shrink-0">
                        {isCompleted ? (
                          <CheckCircle2 className="w-4 h-4 text-[#2563EB]" />
                        ) : isActive ? (
                          <Loader2 className="w-4 h-4 animate-spin text-[#2563EB]" />
                        ) : (
                          <span className="w-4 h-4 rounded-full border border-[#E5E7EB] dark:border-slate-700 flex items-center justify-center text-[9px] font-bold text-[#6B7280]">
                            {idx + 1}
                          </span>
                        )}
                      </div>
                      <div className="space-y-0.5">
                        <p className={`text-xs ${titleClass}`}>{step.label}</p>
                        {isActive && <p className="text-[10px] text-[#6B7280] leading-normal">{step.desc}</p>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
