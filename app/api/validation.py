from fastapi import APIRouter, Query

from app.quant.validation import create_walk_forward_windows

router = APIRouter()


@router.get("/ml/walk-forward/windows")
async def walk_forward_windows(
    length: int = Query(..., gt=0),
    train_size: int = Query(..., gt=0),
    validation_size: int = Query(..., gt=0),
    test_size: int = Query(..., gt=0),
    step: int | None = Query(None, gt=0),
):
    windows = create_walk_forward_windows(length, train_size, validation_size, test_size, step)
    return {"windows": [window.__dict__ for window in windows], "count": len(windows)}