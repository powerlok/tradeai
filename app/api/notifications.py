from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_user
from app.services.notifications import NotificationService


router = APIRouter()


@router.get("/notifications")
async def list_notifications(user: dict = Depends(require_user)):
    user_id = str(user.get("sub", ""))
    if not user_id:
        raise HTTPException(status_code=403, detail="Usuário inválido")
    service = NotificationService()
    notifications = await service.list_for_user(user_id)
    await service.close()
    return {"notifications": notifications}


@router.delete("/notifications/{notification_id}", status_code=204)
async def delete_notification(notification_id: str, user: dict = Depends(require_user)):
    user_id = str(user.get("sub", ""))
    if not user_id:
        raise HTTPException(status_code=403, detail="Usuário inválido")
    service = NotificationService()
    await service.delete(user_id, notification_id)