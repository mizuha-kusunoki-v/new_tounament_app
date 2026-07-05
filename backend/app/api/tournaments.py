import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Match, Participant, Tournament
from app.models.enums import TournamentStatus
from app.schemas.tournament import (
    MatchReportIn,
    ParticipantCreateIn,
    ParticipantOut,
    TournamentCreateIn,
    TournamentCreatedOut,
    TournamentManageStateOut,
    TournamentStateOut,
)
from app.serializers import build_tournament_state
from app.services import tournament_service
from app.services.tournament_service import TournamentError

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


def _get_by_manage_token(db: Session, manage_token: str) -> Tournament:
    tournament = db.query(Tournament).filter(Tournament.manage_token == manage_token).first()
    if tournament is None:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return tournament


def _get_by_public_slug(db: Session, public_slug: str) -> Tournament:
    tournament = db.query(Tournament).filter(Tournament.public_slug == public_slug).first()
    if tournament is None:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return tournament


@router.post("", response_model=TournamentCreatedOut)
def create_tournament(body: TournamentCreateIn, db: Session = Depends(get_db)):
    tournament = Tournament(
        name=body.name,
        format=body.format,
        public_slug=secrets.token_urlsafe(8),
        manage_token=secrets.token_urlsafe(24),
    )
    db.add(tournament)
    db.commit()
    db.refresh(tournament)
    return TournamentCreatedOut(
        id=tournament.id,
        name=tournament.name,
        manage_token=tournament.manage_token,
        public_slug=tournament.public_slug,
        format=tournament.format,
    )


@router.post("/{manage_token}/participants", response_model=ParticipantOut)
def add_participant(manage_token: str, body: ParticipantCreateIn, db: Session = Depends(get_db)):
    tournament = _get_by_manage_token(db, manage_token)
    if tournament.status != TournamentStatus.SETUP:
        raise HTTPException(status_code=400, detail="Cannot add participants after the tournament has started")
    participant = Participant(tournament_id=tournament.id, display_name=body.display_name)
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


@router.delete("/{manage_token}/participants/{participant_id}", status_code=204)
def remove_participant(manage_token: str, participant_id: uuid.UUID, db: Session = Depends(get_db)):
    tournament = _get_by_manage_token(db, manage_token)
    if tournament.status != TournamentStatus.SETUP:
        raise HTTPException(status_code=400, detail="Cannot remove participants after the tournament has started")
    participant = (
        db.query(Participant)
        .filter(Participant.id == participant_id, Participant.tournament_id == tournament.id)
        .first()
    )
    if participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    db.delete(participant)
    db.commit()


@router.post("/{manage_token}/start", response_model=TournamentManageStateOut)
def start_tournament(manage_token: str, db: Session = Depends(get_db)):
    tournament = _get_by_manage_token(db, manage_token)
    try:
        tournament_service.start_tournament(db, tournament)
    except TournamentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.refresh(tournament)
    return build_tournament_state(tournament, include_manage_token=True)


@router.get("/{manage_token}/manage", response_model=TournamentManageStateOut)
def get_manage_state(manage_token: str, db: Session = Depends(get_db)):
    tournament = _get_by_manage_token(db, manage_token)
    return build_tournament_state(tournament, include_manage_token=True)


@router.get("/public/{public_slug}", response_model=TournamentStateOut)
def get_public_state(public_slug: str, db: Session = Depends(get_db)):
    tournament = _get_by_public_slug(db, public_slug)
    return build_tournament_state(tournament, include_manage_token=False)


@router.post("/{manage_token}/matches/{match_id}/report", response_model=TournamentManageStateOut)
def report_match(manage_token: str, match_id: uuid.UUID, body: MatchReportIn, db: Session = Depends(get_db)):
    tournament = _get_by_manage_token(db, manage_token)
    match = (
        db.query(Match)
        .join(Match.bracket_round)
        .filter(Match.id == match_id, Match.bracket_round.has(tournament_id=tournament.id))
        .first()
    )
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    try:
        tournament_service.report_match_result(db, tournament, match, body.winner_team_id)
    except TournamentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.refresh(tournament)
    return build_tournament_state(tournament, include_manage_token=True)
