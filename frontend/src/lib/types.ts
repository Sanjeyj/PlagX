export interface User {
  id: string;
  email: string;
  full_name: string;
}

export interface Document {
  id: string;
  original_name: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  upload_date: string;
  has_report: boolean;
}

export interface HighlightSpan {
  start_char: number;
  end_char: number;
  match_type: string;
  similarity: number;
  source_index: number;
  source_name: string;
  group_type?: string;
  overlapping_sources?: Array<{
    source_id: string;
    source_name: string;
    match_type: string;
    similarity: number;
    source_index?: number;
  }>;
  top_source_id?: string;
}

export interface MatchedSource {
  source_index: number;
  source_name: string;
  match_percentage: number;
  color: string;
  matched_spans?: HighlightSpan[];
}

export interface ParagraphScore {
  paragraph_index: number;
  text: string;
  score: number;
  match_type: string | null;
}

export interface Report {
  id: string;
  document_id: string;
  document_name: string;
  overall_score: number;
  exact_score: number;
  semantic_score: number;
  source_density_score: number;
  risk_level: string;
  total_words: number;
  total_pages: number;
  total_sources: number;
  highlights: HighlightSpan[];
  matched_sources: MatchedSource[];
  paragraph_scores: ParagraphScore[];
  full_text: string;
  pdf_status: string;
  created_at: string;
}

export interface DashboardStats {
  total_documents: number;
  total_reports: number;
  average_score: number;
  high_risk_count: number;
  recent_reports: any[];
}
