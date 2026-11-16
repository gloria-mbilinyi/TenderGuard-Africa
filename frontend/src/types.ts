export type ViewName = "overview" | "documents" | "evaluate" | "reports" | "settings";

export interface BrowserSession {
  authenticated: true;
  csrf_token: string;
  expires_at: string;
  auth_mode: "LOCAL_DEMO_SESSION";
}

export interface CatalogRequirement {
  code: string;
  label: string;
}

export interface CatalogBid {
  bid_id: string;
  supplier_name: string;
  supplier_identifier: string | null;
  amount: number;
  currency: string;
  submitted_at: string;
  submitted_document_codes: string[];
  synthetic: true;
}

export interface CatalogTender {
  tender_id: string;
  ocid: string | null;
  title: string;
  description: string;
  status: string;
  procurement_method: string;
  submission_deadline: string;
  amount: number;
  currency: string;
  procuring_entity: string;
  required_documents: CatalogRequirement[];
  eligibility_requirements: CatalogRequirement[];
  bids: CatalogBid[];
  source_file: string;
  synthetic: true;
}

export interface CatalogResponse {
  tenders: CatalogTender[];
}

export interface TenderEvidence {
  ocid: string | null;
  tender_id: string;
  title: string | null;
  description: string | null;
  status: string | null;
  procurement_method: string | null;
  amount: number | null;
  currency: string | null;
  procuring_entity: string | null;
  source_file: string;
}

export interface ComplianceCheck {
  criterion: string;
  passed: boolean;
  finding: string;
  sources: string[];
}

export interface ComplianceEvidence {
  tender_id: string;
  bid_id: string;
  supplier: string | null;
  status: "COMPLIANT" | "NON_COMPLIANT";
  summary: {
    total_checks: number;
    passed_checks: number;
    failed_checks: number;
  };
  checks: ComplianceCheck[];
  source_files: string[];
}

export interface PriceEvidence {
  bid_id: string;
  supplier: string | null;
  bid_price: number;
  currency: string;
  historical_statistics: {
    sample_size: number;
    minimum: number;
    median: number;
    maximum: number;
  };
  difference_from_median: number;
  deviation_percentage: number | null;
  risk_level: string;
  finding: string;
  sources: { bid: string; historical_awards: string };
  evidence: Array<{
    ocid: string | null;
    award_id: string | null;
    supplier: string | null;
    award_date: string | null;
    amount: number;
    currency: string;
    source_file: string;
  }>;
  decision_note: string;
}

export interface SupplierRiskEvidence {
  bid_id: string;
  supplier_name: string | null;
  supplier_identifier: string | null;
  risk_level: string;
  flag_count: number;
  flags: Array<{
    code: string;
    severity: string;
    finding: string;
    sources: string[];
    evidence: Record<string, unknown> | null;
  }>;
  historical_records_checked: number;
  evidence: Array<Record<string, unknown>>;
  source_files: string[];
  review_note: string;
}

export interface EvaluationResult {
  evaluation_id: string;
  completed_at: string;
  tender_id: string;
  bid_id: string;
  status: "AWAITING_HUMAN_REVIEW";
  completed_tools: string[];
  decision_support: {
    review_priority: "STANDARD_REVIEW" | "ATTENTION_REQUIRED";
    summary: string;
    reasons: string[];
    human_committee_required: true;
    final_award_decision: null;
  };
  tender: TenderEvidence | null;
  compliance: ComplianceEvidence | null;
  price_analysis: PriceEvidence | null;
  supplier_risk: SupplierRiskEvidence | null;
  human_committee_required: true;
  final_award_decision: null;
}

export interface EvaluationSummary {
  evaluation_id: string;
  completed_at: string;
  tender_id: string;
  bid_id: string;
  supplier: string | null;
  status: "AWAITING_HUMAN_REVIEW";
  review_priority: "STANDARD_REVIEW" | "ATTENTION_REQUIRED";
  final_award_decision: null;
}

export interface ReportItem {
  filename: string;
  bid_id: string;
  tender_title?: string | null;
  supplier_names?: string[];
  workspace_id?: string | null;
  generated_at?: string | null;
  approved_by?: string | null;
  authorizer_identity_verified?: false;
  status: "DRAFT_FOR_COMMITTEE_REVIEW";
  size_bytes: number;
  modified_at: string;
  download_url: string;
}

export interface SystemStatus {
  api_status: "AVAILABLE";
  api_version: string;
  ai_provider: "OLLAMA";
  model: string;
  model_status: "AVAILABLE" | "MODEL_MISSING" | "UNAVAILABLE";
  authentication: "LOCAL_DEMO_SESSION";
  secrets_exposed_to_browser: false;
}

export interface UploadedDocument {
  document_id: string;
  document_type: "TENDER_REQUIREMENTS" | "SUPPLIER_BID";
  filename: string;
  supplier_name: string | null;
  content_type: "application/pdf";
  size_bytes: number;
  page_count: number;
  sha256: string;
  uploaded_at: string;
  extraction_status: "TEXT_EXTRACTED";
  pdf_metadata: Record<string, string | null>;
  extracted_preview?: string | null;
}

export interface DocumentWorkspace {
  workspace_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  status: "DOCUMENTS_PENDING" | "READY_FOR_EVALUATION" | "AWAITING_HUMAN_REVIEW";
  documents: UploadedDocument[];
  latest_evaluation_id: string | null;
}

export interface PageCitation {
  document_id: string;
  filename: string;
  page: number;
  quote: string;
}

export interface ExtractedField {
  value: string | number | null;
  status: "VERIFIED" | "NOT_FOUND" | "AMBIGUOUS";
  sources: PageCitation[];
}

export interface RequirementFinding {
  code: string;
  requirement: string;
  status:
    | "VERIFIED_COMPLIANT"
    | "VERIFIED_NONCOMPLIANT"
    | "MISSING_EVIDENCE"
    | "REQUIRES_HUMAN_REVIEW"
    | "UNVERIFIED";
  finding: string;
  sources: PageCitation[];
}

export interface DocumentSupplierEvaluation {
  document_id: string;
  filename: string;
  supplier_name: ExtractedField;
  supplier_identifier: ExtractedField;
  bid_reference: ExtractedField;
  submitted_at: ExtractedField;
  bid_price: ExtractedField;
  currency: ExtractedField;
  document_checks: RequirementFinding[];
  eligibility_checks: RequirementFinding[];
  technical_checks: RequirementFinding[];
  financial_check: RequirementFinding;
  missing_documents: string[];
  risk_flags: Array<{
    code: string;
    severity: "LOW" | "MEDIUM" | "HIGH";
    finding: string;
    sources: PageCitation[];
  }>;
  evidence_status:
    | "COMPLIANT_WITH_AVAILABLE_EVIDENCE"
    | "VERIFIED_NONCOMPLIANT"
    | "EVIDENCE_INCOMPLETE";
}

export interface DocumentEvaluationResult {
  evaluation_id: string;
  workspace_id: string;
  completed_at: string;
  status: "AWAITING_HUMAN_REVIEW";
  completed_tools: string[];
  tender: {
    document_id: string;
    filename: string;
    tender_id: ExtractedField;
    title: ExtractedField;
    procuring_entity: ExtractedField;
    submission_deadline: ExtractedField;
    currency: ExtractedField;
    required_documents: Array<{ code: string; label: string; source: PageCitation }>;
    eligibility_criteria: Array<{ code: string; label: string; source: PageCitation }>;
    technical_specifications: Array<{ code: string; label: string; source: PageCitation }>;
    financial_requirements: Array<{ code: string; label: string; source: PageCitation }>;
    evaluation_criteria: Array<{ code: string; label: string; source: PageCitation }>;
  };
  suppliers: DocumentSupplierEvaluation[];
  comparison: {
    supplier_count: number;
    directly_comparable_prices: boolean;
    price_order: Array<{
      document_id: string;
      supplier_name: string;
      amount: number;
      currency: string;
      source: PageCitation;
    }>;
    historical_price_comparison_performed: false;
    notes: string[];
  };
  decision_support: {
    review_priority: "STANDARD_REVIEW" | "ATTENTION_REQUIRED";
    summary: string;
    reasons: string[];
    human_committee_required: true;
    final_award_decision: null;
  };
  human_committee_required: true;
  final_award_decision: null;
}
