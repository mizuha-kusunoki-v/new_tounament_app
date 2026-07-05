import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import require_admin
from app.auth.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import AdminUser, Tournament
from app.schemas.admin import (
    AdminCreateUserIn,
    AdminLoginIn,
    AdminLoginOut,
    AdminMeOut,
    AdminTournamentListItemOut,
    AdminUserOut,
)
from app.services.tournament_service import delete_tournament_cascade

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/login", response_model=AdminLoginOut)
def login(body: AdminLoginIn, db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter(AdminUser.username == body.username).first()
    if admin is None or not admin.is_active or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return AdminLoginOut(access_token=create_access_token(admin.username))


@router.get("/me", response_model=AdminMeOut)
def me(admin: AdminUser = Depends(require_admin)):
    return AdminMeOut(username=admin.username)


@router.get("/tournaments", response_model=list[AdminTournamentListItemOut])
def list_all_tournaments(db: Session = Depends(get_db), admin: AdminUser = Depends(require_admin)):
    return db.query(Tournament).order_by(Tournament.created_at.desc()).all()


@router.delete("/tournaments/{tournament_id}", status_code=204)
def delete_tournament(
    tournament_id: uuid.UUID, db: Session = Depends(get_db), admin: AdminUser = Depends(require_admin)
):
    tournament = db.get(Tournament, tournament_id)
    if tournament is None:
        raise HTTPException(status_code=404, detail="Tournament not found")
    delete_tournament_cascade(db, tournament)


@router.post("/users", response_model=AdminUserOut, status_code=201)
def create_admin_user(
    body: AdminCreateUserIn, db: Session = Depends(get_db), admin: AdminUser = Depends(require_admin)
):
    if db.query(AdminUser).filter(AdminUser.username == body.username).first():
        raise HTTPException(status_code=409, detail="Username already taken")
    new_admin = AdminUser(username=body.username, password_hash=hash_password(body.password))
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return new_admin
