"""
Enhanced Type Definitions for GraphShift OSS Services
Replaces generic Dict[str, Any] with specific, meaningful types
"""

from typing import Dict, List, Optional, Any, Union, Literal, Tuple, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# ==================== CONFIGURATION TYPES ====================

@dataclass
class ServiceConfig:
    """Service-specific configuration"""
    timeout_seconds: int = 30
    max_file_size_kb: int = 500
    batch_size: int = 10
    memory_limit_mb: int = 256

@dataclass
class TelemetryConfig:
    """Telemetry configuration"""
    enabled: bool = True
    track_operations: bool = True
    track_features: bool = True
    track_performance: bool = True
    max_metrics_memory: int = 1000

@dataclass
class GraphShiftConfig:
    """Main GraphShift configuration"""
    version: str
    scm: Dict[str, Any]  # Will be refined further
    knowledge_base: Dict[str, Any]  # Will be refined further
    telemetry: TelemetryConfig
    output: Dict[str, Any]  # Will be refined further

# ==================== HEALTH CHECK TYPES ====================

@dataclass
class ServiceHealthDetails:
    """Detailed health check information"""
    service_name: str
    config_loaded: bool
    timestamp: str
    jar_path: Optional[str] = None
    jar_size_bytes: Optional[int] = None
    patterns_loaded: Optional[int] = None
    github_token_configured: Optional[bool] = None
    error: Optional[str] = None
    error_type: Optional[str] = None

@dataclass
class TelemetryMetrics:
    """Service telemetry metrics"""
    service_name: str
    telemetry_enabled: bool
    uptime_seconds: float
    operations: Dict[str, 'OperationMetrics']
    features: Dict[str, 'FeatureMetrics']
    performance: Dict[str, 'PerformanceMetric']
    health_checks: int
    config_validated: bool

@dataclass
class OperationMetrics:
    """Metrics for a specific operation"""
    count: int
    total_time: float
    errors: int
    avg_time: float

@dataclass
class FeatureMetrics:
    """Metrics for feature usage"""
    count: int
    last_used: Optional[str]
    metadata: Dict[str, Any]

@dataclass
class PerformanceMetric:
    """Performance metric value"""
    value: float
    timestamp: str

# ==================== OUTPUT SERVICE TYPES ====================

@dataclass
class FileBreakdownEntry:
    """File breakdown entry for output"""
    file_path: str
    pattern_matches: int
    severity_counts: Dict[str, int]
    estimated_effort: str
    migration_priority: str

@dataclass
class PatternBreakdownEntry:
    """Pattern breakdown entry for output"""
    pattern_id: str
    pattern_name: str
    occurrences: int
    affected_files: int
    severity: str
    remediation_strategy: str

@dataclass
class RecommendationItem:
    """Migration recommendation"""
    title: str
    description: str
    priority: Literal["high", "medium", "low"]
    estimated_effort: str
    affected_files: List[str]
    suggested_approach: str

@dataclass
class AnalysisMetadata:
    """Metadata for analysis results"""
    repository: str
    scan_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    from_version: str = "8"
    to_version: str = "11"
    total_files_analyzed: int = 0
    total_methods_found: int = 0

# ==================== EVENT BUS TYPES ====================

@dataclass
class EventData:
    """Event data for event bus"""
    event_type: str
    timestamp: str
    source_service: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None

# ==================== INSIGHT CARD TYPES ====================

@dataclass
class InsightCard:
    """Insight card for output"""
    title: str
    type: Literal["warning", "info", "success", "error"]
    content: str
    priority: Literal["high", "medium", "low"]
    actionable: bool
    estimated_effort: Optional[str] = None
    affected_components: List[str] = None

# ==================== ANALYSIS RESULT TYPES ====================

@dataclass
class RepositoryAnalysisResult:
    """Complete repository analysis result"""
    metadata: AnalysisMetadata
    file_breakdown: Dict[str, FileBreakdownEntry]
    pattern_breakdown: Dict[str, PatternBreakdownEntry]
    recommendations: List[RecommendationItem]
    insight_cards: List[InsightCard]
    migration_readiness: str
    estimated_effort: str
    pro_preview: Optional[Dict[str, Any]] = None

@dataclass
class OrganizationAnalysisResult:
    """Organization-wide analysis result"""
    org_name: str
    total_repositories: int
    analyzed_repositories: int
    repository_results: List[RepositoryAnalysisResult]
    org_summary: Dict[str, Any]  # Will be refined
    migration_roadmap: List[str]
    timestamp: str

# ==================== SYSTEM INFO TYPES ====================

@dataclass
class SystemTelemetryInfo:
    """System-level telemetry information"""
    total_services_initialized: int
    telemetry_enabled_services: int
    overall_uptime_seconds: float
    total_operations_tracked: int
    total_features_used: int

# ==================== TYPE ALIASES ====================

# Configuration types
ConfigDict = Dict[str, Union[str, int, bool, List[str], Dict[str, Any]]]
ServiceConfigDict = Dict[str, ServiceConfig]

# Health check return types
HealthCheckResult = Tuple['ServiceHealthStatus', ServiceHealthDetails]
DetailedHealthResult = Dict[str, Union[str, int, bool, ServiceHealthDetails, TelemetryMetrics]]

# Analysis return types
AnalysisResult = Tuple[Optional[RepositoryAnalysisResult], Optional[str]]
SummaryResult = Tuple[Optional[Dict[str, Any]], Optional[str]]

# Event types
EventHandler = Callable[[EventData], None]
AsyncEventHandler = Callable[[EventData], Awaitable[None]]

# ==================== UTILITY FUNCTIONS ====================

def create_default_telemetry_config() -> TelemetryConfig:
    """Create default telemetry configuration"""
    return TelemetryConfig()

def create_analysis_metadata(repository: str, scan_id: str) -> AnalysisMetadata:
    """Create analysis metadata with defaults"""
    return AnalysisMetadata(
        repository=repository,
        scan_id=scan_id,
        start_time=datetime.now()
    )

def create_empty_telemetry_metrics(service_name: str) -> TelemetryMetrics:
    """Create empty telemetry metrics for a service"""
    return TelemetryMetrics(
        service_name=service_name,
        telemetry_enabled=False,
        uptime_seconds=0.0,
        operations={},
        features={},
        performance={},
        health_checks=0,
        config_validated=False
    ) 