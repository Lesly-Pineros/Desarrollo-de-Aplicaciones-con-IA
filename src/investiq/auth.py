import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlmodel import Session, select

from investiq.data.models import AppUser, AuthSession

_hasher = PasswordHasher()
SESSION_HOURS = 12


def _email(value: str) -> str:
    return value.strip().casefold()


def authenticate(session: Session, email: str, password: str, configured_email: str) -> str | None:
    target = _email(configured_email)
    candidate = _email(email)
    if not target or candidate != target or not password:
        return None
    user = session.get(AppUser, target)
    if user is None:
        if session.exec(select(AppUser)).first() is not None:
            return None
        user = AppUser(email=target, password_hash=_hasher.hash(password))
        session.add(user)
        session.commit()
    else:
        try:
            if not _hasher.verify(user.password_hash, password):
                return None
        except VerifyMismatchError:
            return None
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    session.add(AuthSession(session_hash=digest, email=target, created_at=now,
                            expires_at=now + timedelta(hours=SESSION_HOURS)))
    session.commit()
    return token


def validate_session(session: Session, token: str | None, configured_email: str) -> str | None:
    if not token or not configured_email:
        return None
    digest = hashlib.sha256(token.encode()).hexdigest()
    record = session.get(AuthSession, digest)
    now = datetime.now(timezone.utc)
    if record is None:
        return None
    expires = record.expires_at.replace(tzinfo=timezone.utc) if record.expires_at.tzinfo is None else record.expires_at
    if expires <= now or record.email != _email(configured_email):
        session.delete(record)
        session.commit()
        return None
    return record.email


def logout(session: Session, token: str | None) -> None:
    if token:
        digest = hashlib.sha256(token.encode()).hexdigest()
        record = session.get(AuthSession, digest)
        if record:
            session.delete(record)
            session.commit()
