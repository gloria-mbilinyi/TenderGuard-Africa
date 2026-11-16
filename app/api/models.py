from typing import Any, Literal

from pydantic import BaseModel, Field

IdentifierField = Field(
    min_length=1,
    max_length=64,
    pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$",
)


class EvaluationRequest(BaseModel):
    tender_id: str = IdentifierField
    bid_id: str = IdentifierField


class TenderEvidence(BaseModel):
    ocid: str | None = None
    tender_id: str
    title: str | None = None
    description: str | None = None
    status: str | None = None
    procurement_method: str | None = None
    amount: int | float | None = None
    currency: str | None = None
    procuring_entity: str | None = None
    source_file: str


class ComplianceCheck(BaseModel):
    criterion: str
    passed: bool
    finding: str
    sources: list[str]


class ComplianceSummary(BaseModel):
    total_checks: int
    passed_checks: int
    failed_checks: int


class ComplianceEvidence(BaseModel):
    tender_id: str
    bid_id: str
    supplier: str | None = None
    status: Literal["COMPLIANT", "NON_COMPLIANT"]
    summary: ComplianceSummary
    checks: list[ComplianceCheck]
    source_files: list[str]


class HistoricalStatistics(BaseModel):
    sample_size: int
    minimum: int | float
    median: int | float
    maximum: int | float


class HistoricalAwardEvidence(BaseModel):
    ocid: str | None = None
    award_id: str | None = None
    supplier: str | None = None
    award_date: str | None = None
    amount: int | float
    currency: str
    source_file: str


class PriceSources(BaseModel):
    bid: str
    historical_awards: str


class PriceEvidence(BaseModel):
    bid_id: str
    supplier: str | None = None
    bid_price: int | float
    currency: str
    historical_statistics: HistoricalStatistics
    difference_from_median: int | float
    deviation_percentage: float | None = None
    risk_level: str
    finding: str
    sources: PriceSources
    evidence: list[HistoricalAwardEvidence]
    decision_note: str


class SupplierFlag(BaseModel):
    code: str
    severity: str
    finding: str
    sources: list[str]
    evidence: dict[str, Any] | None = None


class SupplierHistoryEvidence(BaseModel):
    ocid: str | None = None
    award_id: str | None = None
    supplier_identifier: str | None = None
    supplier_name: str | None = None
    buyer: str | None = None
    amount: int | float | None = None
    currency: str | None = None
    source_file: str


class SupplierRiskEvidence(BaseModel):
    bid_id: str
    supplier_name: str | None = None
    supplier_identifier: str | None = None
    risk_level: str
    flag_count: int
    flags: list[SupplierFlag]
    historical_records_checked: int
    evidence: list[SupplierHistoryEvidence]
    source_files: list[str]
    review_note: str


class DecisionSupport(BaseModel):
    review_priority: Literal["STANDARD_REVIEW", "ATTENTION_REQUIRED"]
    summary: str
    reasons: list[str] = Field(default_factory=list)
    human_committee_required: Literal[True] = True
    final_award_decision: None = None


class EvaluationResponse(BaseModel):
    evaluation_id: str
    completed_at: str
    tender_id: str
    bid_id: str
    status: Literal["AWAITING_HUMAN_REVIEW"]
    completed_tools: list[str]
    decision_support: DecisionSupport
    tender: TenderEvidence | None = None
    compliance: ComplianceEvidence | None = None
    price_analysis: PriceEvidence | None = None
    supplier_risk: SupplierRiskEvidence | None = None
    human_committee_required: Literal[True] = True
    final_award_decision: None = None


class CatalogRequirement(BaseModel):
    code: str
    label: str


class CatalogBid(BaseModel):
    bid_id: str
    supplier_name: str
    supplier_identifier: str | None = None
    amount: int | float
    currency: str
    submitted_at: str
    submitted_document_codes: list[str]
    synthetic: Literal[True] = True


class CatalogTender(BaseModel):
    tender_id: str
    ocid: str | None = None
    title: str
    description: str
    status: str
    procurement_method: str
    submission_deadline: str
    amount: int | float
    currency: str
    procuring_entity: str
    required_documents: list[CatalogRequirement]
    eligibility_requirements: list[CatalogRequirement]
    bids: list[CatalogBid]
    source_file: str
    synthetic: Literal[True] = True


class CatalogResponse(BaseModel):
    tenders: list[CatalogTender]


class BrowserLoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class BrowserSessionResponse(BaseModel):
    authenticated: Literal[True] = True
    csrf_token: str
    expires_at: str
    auth_mode: Literal["LOCAL_DEMO_SESSION"] = "LOCAL_DEMO_SESSION"


class EvaluationSummary(BaseModel):
    evaluation_id: str
    completed_at: str
    tender_id: str
    bid_id: str
    supplier: str | None = None
    status: Literal["AWAITING_HUMAN_REVIEW"]
    review_priority: Literal["STANDARD_REVIEW", "ATTENTION_REQUIRED"]
    final_award_decision: None = None


class EvaluationListResponse(BaseModel):
    evaluations: list[EvaluationSummary]


class ReportItem(BaseModel):
    filename: str
    bid_id: str
    status: Literal["DRAFT_FOR_COMMITTEE_REVIEW"]
    size_bytes: int
    modified_at: str
    download_url: str


class ReportListResponse(BaseModel):
    reports: list[ReportItem]
    approval_available_in_browser: Literal[False] = False


class SystemStatusResponse(BaseModel):
    api_status: Literal["AVAILABLE"] = "AVAILABLE"
    api_version: str
    ai_provider: Literal["OLLAMA"] = "OLLAMA"
    model: str
    model_status: Literal["AVAILABLE", "MODEL_MISSING", "UNAVAILABLE"]
    authentication: Literal["LOCAL_DEMO_SESSION"] = "LOCAL_DEMO_SESSION"
    secrets_exposed_to_browser: Literal[False] = False
