from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.point import PointLogResponse
from app.services.points_service import PointsService
from app.api.users import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("", response_model=dict)
def get_points_balance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取积分余额"""
    balance = PointsService.get_user_balance(db, current_user.id)
    return {"balance": balance}

@router.get("/logs", response_model=List[PointLogResponse])
def get_point_logs(limit: int = 100, offset: int = 0, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取积分明细"""
    logs = PointsService.get_point_logs(db, current_user.id, limit, offset)
    return logs