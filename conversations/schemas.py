from typing import Any, Literal, Optional, List, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


SenderType = Literal["user", "llm"]


class MessageCreate(BaseModel):
    conversation_id: Optional[int] = Field(default=None, ge=1)
    user_id: Optional[int] = Field(default=None, ge=1)
    sender: SenderType
    text: str = Field(..., min_length=1, max_length=10_000)
    job_sequence_id: Optional[int] = Field(default=None, ge=1)

    model_config = ConfigDict(extra="forbid")


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender: SenderType
    text: str
    sequence_num: int
    job_sequence_id: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobCreate(BaseModel):
    conversation_id: int = Field(..., ge=1)
    job_json: dict

    model_config = ConfigDict(extra="forbid")


class JobResponse(BaseModel):
    id: int
    conversation_id: int
    job_json: dict
    sequence_num: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationMessage(BaseModel):
    type: Literal["message"] = "message"
    id: int
    conversation_id: int
    sender: SenderType
    text: str
    sequence_num: int
    job_sequence_id: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationJob(BaseModel):
    type: Literal["job"] = "job"
    id: int
    conversation_id: int
    job_json: dict
    sequence_num: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


ConversationItem = Union[ConversationMessage, ConversationJob]


class ConversationStreamResponse(BaseModel):
    conversation_id: int
    items: List[ConversationItem]


class ConversationCreatedResponse(BaseModel):
    conversation_id: int


class ConversationSummary(BaseModel):
    id: int
    user_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    last_sequence_num: int

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    conversations: List[ConversationSummary]

