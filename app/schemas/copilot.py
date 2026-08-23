from pydantic import BaseModel, Field
class CopilotChatRequest(BaseModel):
    scan_id: str
    message: str = Field(min_length=1,max_length=2000)
class CopilotChatResponse(BaseModel):
    scan_id: str; reply: str; grounded_in_evidence_ids: list[str]=Field(default_factory=list); is_demo_provider: bool
class CommunityReportRequest(BaseModel):
    scan_id: str|None=None
    description: str=Field(min_length=1,max_length=5000)
class CommunityReportResponse(BaseModel):
    id: str; status: str="RECEIVED"
