from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.key import ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse
from app.services.key_service import KeyService
from app.services.router_service import PROVIDER_BASE_URLS
from app.api.users import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("", response_model=ApiKeyResponse)
def create_api_key(request: ApiKeyCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """创建API密钥"""
    # 厂商密钥必须在白名单内（安全策略：防止 SSRF）
    if request.key_type == 2:
        if not request.provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="厂商密钥必须指定 provider"
            )
        if request.provider.lower() not in PROVIDER_BASE_URLS:
            allowed = list(PROVIDER_BASE_URLS.keys())
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的 provider '{request.provider}'，当前支持：{allowed}"
            )
    try:
        api_key = KeyService.create_api_key(
            db=db,
            user_id=current_user.id,
            key_type=request.key_type,
            name=request.name,
            provider=request.provider,
            raw_key=request.encrypted_key
        )
        return api_key
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("", response_model=List[ApiKeyResponse])
def get_api_keys(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取密钥列表"""
    keys = KeyService.get_user_keys(db, current_user.id)
    return keys

@router.put("/{key_id}", response_model=ApiKeyResponse)
def update_api_key(key_id: int, request: ApiKeyUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """更新密钥状态"""
    key = KeyService.get_key_by_id(db, key_id)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="密钥不存在"
        )
    
    if key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作此密钥"
        )
    
    if request.name is not None:
        key.name = request.name
    if request.status is not None:
        # 走 update_key_status 确保同步清缓存（available_keys / api_key）
        KeyService.update_key_status(db, key_id, request.status)
        db.refresh(key)
        return key

    db.commit()
    db.refresh(key)
    return key

@router.delete("/{key_id}")
def delete_api_key(key_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除密钥"""
    key = KeyService.get_key_by_id(db, key_id)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="密钥不存在"
        )
    
    if key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作此密钥"
        )
    
    # 软删除，将状态设置为1
    KeyService.update_key_status(db, key_id, 1)
    return {"message": "密钥已删除"}