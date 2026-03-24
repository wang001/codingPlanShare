from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.point import PointLogResponse
from app.services.points_service import PointsService
from app.api.users import get_current_user
from app.models.user import User

router = APIRouter()


@router.get(
    "",
    response_model=dict,
    summary="获取积分余额",
    description=(
        "返回当前用户的实时积分余额。\n\n"
        "余额从内存读取（极快），每秒异步落库，服务启动时从数据库加载。"
    ),
)
def get_points_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    balance = PointsService.get_user_balance(db, current_user.id)
    return {"balance": balance}


@router.get(
    "/logs",
    response_model=List[PointLogResponse],
    summary="获取积分明细",
    description=(
        "返回当前用户的积分变动记录，按时间倒序排列。\n\n"
        "**type 字段枚举**：\n"
        "- `1` 调用消耗：使用平台密钥调用对话接口，按次扣减\n"
        "- `2` 托管收益：用户的厂商密钥被平台调用，自动获得奖励\n"
        "- `3` 管理员调整：管理员手动增减\n"
        "- `4` 平台收入：平台抽取差价（当前版本预留，未启用）\n\n"
        "**注意**：只返回已落库的记录（最多延迟 1 秒），"
        "正在进行中的扣费可能暂时未出现在此列表。"
    ),
)
def get_point_logs(
    limit: int = Query(default=100, ge=1, le=500, description="返回条数上限，最大 500"),
    offset: int = Query(default=0, ge=0, description="分页偏移量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logs = PointsService.get_point_logs(db, current_user.id, limit, offset)
    return logs
