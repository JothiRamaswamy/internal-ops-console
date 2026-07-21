from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.services.overview_service import get_overview

router = APIRouter(prefix="/api/overview", tags=["overview"])


@router.get("")
def overview(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    return get_overview(db)
