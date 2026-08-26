from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import require_admin, require_user
from app.services.operational_state import OPERATIONAL_STATES, entry_enabled, get_operational_state, set_operational_state

router = APIRouter()


class OperationalStateRequest(BaseModel):
    state: str = Field(min_length=3, max_length=20)


@router.get("/operational-state", dependencies=[Depends(require_user)])
async def operational_state():
    state = await get_operational_state()
    return {"state": state, "available_states": sorted(OPERATIONAL_STATES), "entry_enabled": entry_enabled(state)}


@router.put("/admin/operational-state", dependencies=[Depends(require_admin)])
async def update_operational_state(payload: OperationalStateRequest):
    state = await set_operational_state(payload.state)
    return {"state": state, "entry_enabled": entry_enabled(state)}