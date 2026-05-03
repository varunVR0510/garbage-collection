from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import db

router = APIRouter()


class FeedbackIn(BaseModel):
    district: str = Field(..., min_length=1, max_length=64)
    actual_tons: float = Field(..., ge=0, le=10000)
    note: Optional[str] = Field(None, max_length=500)


@router.post("")
def submit_feedback(payload: FeedbackIn):
    try:
        db.log_feedback(payload.district, float(payload.actual_tons), payload.note)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record feedback: {e}")
    return {"ok": True}


@router.get("")
def get_feedback():
    return db.list_feedback(limit=50)
