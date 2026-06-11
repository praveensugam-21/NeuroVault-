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

  // The 15 pipeline steps from Section 8
  const pipelineSteps: PipelineStep[] = [
    { label: 'File Upload & Type Detection', desc: 'Parsing binary stream headers and validating formats.' },
    { label: 'OpenCV Pre-processing', desc: 'De-skewing tilt, running gaussian denoise, and enhancing contrast.' },
    { label: 'OCR / Vision AI Analysis', desc: 'Reading document text blocks via Gemini Vision / local EasyOCR.' },
    { label: 'Taxonomy Classification', desc: 'Validating card headers against our 50+ document taxonomy.' },
    { label: 'Structured Field Extraction', desc: 'Generating specific JSON schema fields from text payload.' },
    { label: 'Format Validation Checks', desc: 'Checking PAN, Aadhaar, dates, and GSTIN formatting matches.' },
    { label: 'Quality Score Assessment', desc: 'Calculating extraction completeness & character confidence.' },
    { label: 'Summary Card Generation', desc: 'Writing a natural language summary explaining document assets.' },
    { label: 'spaCy Named Entity Mining', desc: 'Extracting names of persons, dates, locations, and organizations.' },
    { label: 'Embedding Computation', desc: 'Converting summaries and metadata strings to 384-dim vector representations.' },
    { label: 'Vector Store Insertion', desc: 'Saving document vector embeddings to local ChromaDB database.' },
    { label: 'Knowledge Graph Linking', desc: 'Scanning existing files for matching entities to draw relationship links.' },
    { label: 'Action Items & Deadlines Check', desc: 'Parsing document fields for expiry alerts and billing due dates.' },
    { label: 'Auto-Tagging & Folder Routing', desc: 'Creating folder markers and tagging files (e.g. #identity, #cbse).' },
    { label: 'User Completion Notification', desc: 'Saving record state to SQLite relational tables and updating view.' }
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
      await api.post('/api/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      
      // Simulate/trigger steps update locally for a smooth UI experience
      // during local background processing thread execution.
      for (let i = 1; i < pipelineSteps.length; i++) {
        await new Promise((resolve) => setTimeout(resolve, 550));
        setCurrentStepIndex(i);
      }

      setSuccess(true);
      await fetchDocuments();
      await fetchStats();
      setFile(null);
      setCustomName('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to complete document upload pipeline.');
      setPipelineActive(false);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8 h-full overflow-y-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Upload Center</h1>
        <p className="text-muted-foreground text-sm">
          Submit files to execute the universal 15-step semantic parsing and extraction pipeline.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* Upload form panel */}
        <div className="bg-card border border-border p-6 rounded-lg space-y-6 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Select File</h2>
          
          <form onSubmit={handleUploadSubmit} className="space-y-6">
            {/* Drag drop zone */}
            <div className="border border-dashed border-border rounded-lg p-8 bg-background/50 hover:bg-background transition-all text-center relative group cursor-pointer">
              <input
                type="file"
                onChange={handleFileChange}
                accept=".pdf,.png,.jpg,.jpeg,.mp3,.wav,.m4a,.txt"
                className="absolute inset-0 opacity-0 cursor-pointer"
                disabled={uploading}
              />
              <div className="flex flex-col items-center justify-center gap-3">
                <FileUp className="w-8 h-8 text-muted-foreground group-hover:text-primary transition-colors" />
                <div className="space-y-1">
                  <p className="text-xs font-semibold">{file ? file.name : 'Click to browse files'}</p>
                  <p className="text-[10px] text-muted-foreground">
                    PDF, Image (PNG, JPG), Audio (MP3, WAV), Text (TXT)
                  </p>
                </div>
              </div>
            </div>

            {/* Custom Name */}
            {file && (
              <div className="space-y-2">
                <label className="text-[10px] font-semibold text-muted-foreground uppercase">Document Display Name</label>
                <input
                  type="text"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  placeholder="Enter custom document name"
                  className="w-full bg-background border border-border rounded px-3 py-2 text-xs focus:outline-none focus:border-primary"
                  disabled={uploading}
                />
              </div>
            )}

            {error && (
              <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900 text-red-800 dark:text-red-400 p-3 rounded text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {success && (
              <div className="bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900 text-emerald-800 dark:text-emerald-400 p-3 rounded text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                <span>Document successfully processed and archived. Check folders in Vault!</span>
              </div>
            )}

            <button
              type="submit"
              disabled={!file || uploading}
              className="w-full bg-primary text-primary-foreground hover:bg-primary/95 py-2.5 rounded text-xs font-semibold flex items-center justify-center gap-2 disabled:opacity-50 disabled:hover:bg-primary transition-colors"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Running Pipeline
                </>
              ) : (
                'Process Document'
              )}
            </button>
          </form>
        </div>

        {/* Pipeline progression visualizer panel */}
        {pipelineActive && (
          <div className="bg-card border border-border p-6 rounded-lg space-y-6 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Pipeline Progression</h2>
            
            <div className="space-y-4 max-h-[380px] overflow-y-auto pr-1">
              {pipelineSteps.map((step, idx) => {
                const isCompleted = idx < currentStepIndex;
                const isActive = idx === currentStepIndex;

                let textColor = 'text-muted-foreground/50';
                let borderStyle = 'border-border/40';

                if (isCompleted) {
                  textColor = 'text-muted-foreground';
                  borderStyle = 'border-primary/20 bg-primary/5';
                } else if (isActive) {
                  textColor = 'text-foreground font-semibold';
                  borderStyle = 'border-primary shadow-sm bg-primary/10';
                }

                return (
                  <div 
                    key={idx} 
                    className={`flex items-start gap-3 p-2.5 border rounded-lg transition-all ${borderStyle}`}
                  >
                    <div className="mt-0.5">
                      {isCompleted ? (
                        <CheckCircle2 className="w-4 h-4 text-primary" />
                      ) : isActive ? (
                        <Loader2 className="w-4 h-4 animate-spin text-primary" />
                      ) : (
                        <span className="w-4 h-4 rounded-full border border-border/60 flex items-center justify-center text-[8px] font-bold text-muted-foreground/45">
                          {idx + 1}
                        </span>
                      )}
                    </div>
                    <div className="space-y-0.5">
                      <p className={`text-xs ${textColor}`}>{step.label}</p>
                      {isActive && <p className="text-[10px] text-muted-foreground leading-normal">{step.desc}</p>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
