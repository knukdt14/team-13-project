"""네 영역이 공유하는 Pydantic 계약의 단일 import 지점."""

from src.backend.schemas.chat import (
    AnswerResult,
    AskRequest,
    AskResponse,
    EligibilityResponse,
    FeedbackRequest,
    Message,
    SearchResult,
    Source,
)
from src.backend.schemas.common import ErrorResponse, HealthResponse, OkResponse, Page
from src.backend.schemas.document import AttachmentInfo, DeleteResponse, UploadResponse
from src.backend.schemas.policy import PolicyCard, PolicyDetail, PolicyListResponse
from src.backend.schemas.profile import (
    CodesResponse,
    EmploymentStatus,
    MetaResponse,
    SearchMode,
    SidoOption,
    UserProfile,
)
from src.backend.schemas.region import GeoJsonResponse, RegionCount, RegionSummaryResponse

__all__ = [
    "AnswerResult", "AskRequest", "AskResponse", "AttachmentInfo", "CodesResponse",
    "DeleteResponse", "EligibilityResponse", "EmploymentStatus", "ErrorResponse",
    "FeedbackRequest", "GeoJsonResponse", "HealthResponse", "Message", "MetaResponse", "OkResponse", "Page", "PolicyCard",
    "PolicyDetail", "PolicyListResponse", "RegionCount", "RegionSummaryResponse",
    "SearchMode", "SearchResult", "SidoOption", "Source", "UploadResponse", "UserProfile",
]
