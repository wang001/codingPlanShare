import time
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.auth_service import AuthService
from app.services.points_service import PointsService
from app.services.router_service import RouterService
from app.services.key_service import KeyService
from app.models.call_log import CallLog

router = APIRouter()

@router.post("", response_model=dict)
def create_embeddings(input: str, model: str, api_key: str = Header(...), db: Session = Depends(get_db)):
    """嵌入接口"""
    # 验证API密钥
    key = AuthService.verify_api_key(db, api_key)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API密钥"
        )
    
    # 预扣积分（这里简化处理，实际应该根据模型和请求内容计算积分）
    user_id = key.user_id
    points_to_deduct = 5  # 简化处理，实际应该根据模型和请求内容计算
    
    if not PointsService.pre_deduct_points(db, user_id, points_to_deduct):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="积分余额不足"
        )
    
    # 路由请求到合适的厂商
    route_result = RouterService.route_request(db, model, {"input": input})
    if not route_result:
        # 回滚积分
        PointsService.rollback_points(db, user_id, points_to_deduct)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="没有可用的厂商密钥"
        )
    
    # 调用真实的厂商API
    provider = route_result['provider']
    key_id = route_result['key_id']
    api_key = route_result['key']
    
    # 创建厂商适配器实例
    provider_instance = RouterService.create_provider_instance(provider, api_key)
    if not provider_instance:
        # 回滚积分
        PointsService.rollback_points(db, user_id, points_to_deduct)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"不支持的厂商: {provider}"
        )
    
    try:
        # 调用厂商API
        response = provider_instance.embeddings(
            model=route_result['request']['model'],
            input=input
        )
        
        # 更新密钥使用情况
        KeyService.update_key_usage(db, key_id)
        
        # 确认扣费
        PointsService.confirm_deduct(
            db, user_id, points_to_deduct, 1, key_id, model, f"Embeddings with {provider}"
        )
        
        # 记录调用日志
        call_log = CallLog(
            user_id=user_id,
            provider_key_id=key_id,
            model=model,
            status=1,
            ip="127.0.0.1"  # 实际应该从请求中获取
        )
        db.add(call_log)
        db.commit()
        
        return response
    except Exception as e:
        # 记录错误日志
        call_log = CallLog(
            user_id=user_id,
            provider_key_id=key_id,
            model=model,
            status=0,
            error_msg=str(e),
            ip="127.0.0.1"  # 实际应该从请求中获取
        )
        db.add(call_log)
        db.commit()
        
        # 尝试使用其他密钥
        from app.config.settings import settings
        max_retry = settings.key_management.get('max_retry', 1)
        
        for attempt in range(max_retry):
            # 路由请求到合适的厂商（排除当前失败的密钥）
            route_result = RouterService.route_request(db, model, {"input": input})
            if not route_result:
                break
            
            # 调用真实的厂商API
            provider = route_result['provider']
            key_id = route_result['key_id']
            api_key = route_result['key']
            
            # 创建厂商适配器实例
            provider_instance = RouterService.create_provider_instance(provider, api_key)
            if not provider_instance:
                continue
            
            try:
                # 调用厂商API
                response = provider_instance.embeddings(
                    model=route_result['request']['model'],
                    input=input
                )
                
                # 更新密钥使用情况
                KeyService.update_key_usage(db, key_id)
                
                # 确认扣费
                PointsService.confirm_deduct(
                    db, user_id, points_to_deduct, 1, key_id, model, f"Embeddings with {provider}"
                )
                
                # 记录调用日志
                call_log = CallLog(
                    user_id=user_id,
                    provider_key_id=key_id,
                    model=model,
                    status=1,
                    ip="127.0.0.1"  # 实际应该从请求中获取
                )
                db.add(call_log)
                db.commit()
                
                return response
            except Exception as retry_e:
                # 记录错误日志
                call_log = CallLog(
                    user_id=user_id,
                    provider_key_id=key_id,
                    model=model,
                    status=0,
                    error_msg=str(retry_e),
                    ip="127.0.0.1"  # 实际应该从请求中获取
                )
                db.add(call_log)
                db.commit()
                continue
        
        # 所有重试都失败，回滚积分
        PointsService.rollback_points(db, user_id, points_to_deduct)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"厂商API调用失败: {str(e)}"
        )