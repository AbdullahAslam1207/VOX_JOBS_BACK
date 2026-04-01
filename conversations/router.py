from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from Database.Database_connection import db_dependency
from Database import Tables
from .schemas import (
    MessageCreate,
    MessageResponse,
    JobCreate,
    JobResponse,
    ConversationStreamResponse,
    ConversationMessage,
    ConversationJob,
    ConversationCreatedResponse,
    ConversationListResponse,
    ConversationSummary,
)

router = APIRouter(prefix="/conversation", tags=["conversation"])


def get_or_create_conversation(
    db: Session, conversation_id: Optional[int], user_id: Optional[int]
) -> Tables.Conversation:
    if conversation_id:
        conversation = (
            db.query(Tables.Conversation).filter(Tables.Conversation.id == conversation_id).first()
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found",
            )
        return conversation

    conversation = Tables.Conversation(user_id=user_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_next_sequence_num(db: Session, conversation_id: int) -> int:
    message_max = (
        db.query(func.coalesce(func.max(Tables.Message.sequence_num), 0))
        .filter(Tables.Message.conversation_id == conversation_id)
        .scalar()
    )
    job_max = (
        db.query(func.coalesce(func.max(Tables.JobShown.sequence_num), 0))
        .filter(Tables.JobShown.conversation_id == conversation_id)
        .scalar()
    )
    current_max = max(message_max or 0, job_max or 0)
    return current_max + 1


def validate_job_sequence(db: Session, conversation_id: int, job_sequence_id: int) -> None:
    exists = (
        db.query(Tables.JobShown)
            .filter(
                Tables.JobShown.conversation_id == conversation_id,
                Tables.JobShown.sequence_num == job_sequence_id,
            )
            .first()
    )
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job with sequence {job_sequence_id} was not found in this conversation",
        )

@router.post(
    "/message",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED
)
def create_message(payload: MessageCreate, db: db_dependency):
    conversation = get_or_create_conversation(
        db,
        payload.conversation_id,
        payload.user_id
    )

    if payload.job_sequence_id:
        validate_job_sequence(db, conversation.id, payload.job_sequence_id)

    sequence_num = get_next_sequence_num(db, conversation.id)

    message = Tables.Message(
        conversation_id=conversation.id,
        sender=payload.sender,
        text=payload.text,
        job_sequence_id=payload.job_sequence_id,
        sequence_num=sequence_num,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return MessageResponse.model_validate(message)

@router.post(
    "/job",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED
)
def create_job(payload: JobCreate, db: db_dependency):
    conversation = get_or_create_conversation(db, payload.conversation_id, None)
    sequence_num = get_next_sequence_num(db, conversation.id)

    job = Tables.JobShown(
        conversation_id=conversation.id,
        job_json=payload.job_json,
        sequence_num=sequence_num,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return JobResponse.model_validate(job)


@router.get(
    "/{conversation_id}",
    response_model=ConversationStreamResponse
)
def get_conversation(conversation_id: int, db: db_dependency):
    conversation = (
        db.query(Tables.Conversation).filter(Tables.Conversation.id == conversation_id).first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    messages = (
        db.query(Tables.Message)
        .filter(Tables.Message.conversation_id == conversation_id)
        .all()
    )
    jobs = (
        db.query(Tables.JobShown)
        .filter(Tables.JobShown.conversation_id == conversation_id)
        .all()
    )

    message_items: List[ConversationMessage] = [
        ConversationMessage.model_validate(message) for message in messages
    ]
    job_items: List[ConversationJob] = [ConversationJob.model_validate(job) for job in jobs]

    combined = sorted(message_items + job_items, key=lambda item: item.sequence_num)
    return ConversationStreamResponse(conversation_id=conversation_id, items=combined)


@router.get(
    "",
    response_model=ConversationListResponse
)
def list_conversations(
    user_id: Optional[int],
    db: db_dependency ,
):
    conversations = (
        db.query(Tables.Conversation)
        .filter(Tables.Conversation.user_id == user_id if user_id else True)
        .order_by(Tables.Conversation.created_at.desc())
        .all()
    )

    summaries: List[ConversationSummary] = []
    for conv in conversations:
        last_seq = get_next_sequence_num(db, conv.id) - 1

        msg_latest = (
            db.query(func.coalesce(func.max(Tables.Message.created_at), conv.created_at))
            .filter(Tables.Message.conversation_id == conv.id)
            .scalar()
        )
        job_latest = (
            db.query(func.coalesce(func.max(Tables.JobShown.created_at), conv.created_at))
            .filter(Tables.JobShown.conversation_id == conv.id)
            .scalar()
        )
        updated_at = max(msg_latest or conv.created_at, job_latest or conv.created_at, conv.created_at)

        summaries.append(
            ConversationSummary(
                id=conv.id,
                user_id=conv.user_id,
                created_at=conv.created_at,
                updated_at=updated_at,
                last_sequence_num=last_seq if last_seq > 0 else 0,
            )
        )

    return ConversationListResponse(conversations=summaries)

