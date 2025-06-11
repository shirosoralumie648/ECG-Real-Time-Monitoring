from typing import Any, List

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app import crud, models, schemas
from backend.app.api import deps

router = APIRouter()


@router.post("/", response_model=schemas.User)
def create_user(
    *, 
    db: Session = Depends(deps.get_db), 
    user_in: schemas.UserCreate
) -> Any:
    """
    Create new user.
    """
    user = crud.user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = crud.user.create(db, obj_in=user_in)
    return user
