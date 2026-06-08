"""Pydantic models for competitive analysis data structures."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class SourceType(str, Enum):
    OFFICIAL = "official"
    REVIEW = "review"
    NEWS = "news"
    COMMUNITY = "community"
    OTHER = "other"

class DataPoint(BaseModel):
    """Single collected data point with source traceability."""
    field: str = Field(..., description="Field identifier")
    value: str = Field(..., description="Extracted value")
    source_url: str = Field(..., description="Source URL")
    source_type: SourceType = Field(default=SourceType.OFFICIAL)
    accessed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    confidence: str = Field(default="medium")

class CollectedDimension(BaseModel):
    dimension: str
    data_points: List[DataPoint] = Field(default_factory=list)
    status: str = "complete"

class CollectedData(BaseModel):
    """Output of Collector Agent."""
    competitor: str
    collected_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    dimensions: Dict[str, List[DataPoint]] = Field(default_factory=dict)
    sources: List[Dict[str, str]] = Field(default_factory=list)
    status: str = "success"

class FeatureRow(BaseModel):
    feature: str
    values: Dict[str, int] = Field(default_factory=dict)
    notes: str = ""
    sources: List[Dict[str, str]] = Field(default_factory=list)

class FeatureMatrix(BaseModel):
    features: List[str] = Field(default_factory=list)
    matrix: List[FeatureRow] = Field(default_factory=list)

class SWOTEntry(BaseModel):
    competitor: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    opportunities: List[str] = Field(default_factory=list)
    threats: List[str] = Field(default_factory=list)

class PricingPlan(BaseModel):
    competitor: str
    tier: str
    price: str
    features_included: List[str] = Field(default_factory=list)
    source_url: str = ""

class SentimentProfile(BaseModel):
    competitor: str
    positive_themes: List[str] = Field(default_factory=list)
    negative_themes: List[str] = Field(default_factory=list)
    sentiment_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    sample_size: int = 0
    sources: List[str] = Field(default_factory=list)

class AnalysisResult(BaseModel):
    """Output of Analyst Agent."""
    analysis_id: str = ""
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    competitors: List[str] = Field(default_factory=list)
    feature_matrix: FeatureMatrix = Field(default_factory=FeatureMatrix)
    swot: List[SWOTEntry] = Field(default_factory=list)
    pricing_analysis: List[PricingPlan] = Field(default_factory=list)
    user_sentiment: List[SentimentProfile] = Field(default_factory=list)
    key_insights: List[str] = Field(default_factory=list)

class FinalReport(BaseModel):
    """Output of Writer Agent."""
    report_id: str = ""
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    title: str = ""
    content: str = ""
    word_count: int = 0
    source_count: int = 0
    sections: List[str] = Field(default_factory=list)
    mermaid_diagrams: List[str] = Field(default_factory=list)
