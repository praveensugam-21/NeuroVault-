export interface Tag {
  id: number;
  tag_name: string;
}

export interface DocumentBrief {
  id: string;
  name: string;
  file_type: string;
  category?: string;
  document_type?: string;
  confidence_score: number;
  status: string;
  summary?: string;
  is_locked: boolean;
  created_at: string;
  tags: Tag[];
}

export interface DocumentDetail extends DocumentBrief {
  extracted_json?: any;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatCitation {
  document_id: string;
  document_name: string;
  category: string;
  snippet: string;
  similarity?: number;
  section?: string;
  chunk_index?: number;
}

export interface ChatResponse {
  answer: string;
  citations: ChatCitation[];
  retrieval_method?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'document' | 'entity';
  category: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface TimelineItem {
  id: string;
  name: string;
  document_type: string;
  year?: string | number;
  date?: string;
  detail?: string;
  company?: string;
  designation?: string;
  ctc?: string;
}

export interface ExpiryAlert {
  document_id: string;
  name: string;
  document_type: string;
  expiry_date: string;
  days_remaining: number;
  priority: 'high' | 'medium' | 'low';
}

export interface DashboardStats {
  total_documents: number;
  category_counts: Record<string, number>;
  recent_uploads: any[];
  health_score: number;
  missing_key_documents: string[];
}
