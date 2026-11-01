from sqlmodel import Session, select

from investiq.auth import authenticate, logout, validate_session
from investiq.data.database import create_db, make_engine
from investiq.data.models import AppUser, AuthSession


def test_single_user_argon2_and_hashed_session(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'auth.db'}"))
    with Session(engine) as session:
        token = authenticate(session, "pilot@example.com", "correct horse", "pilot@example.com")
        assert token and validate_session(session, token, "pilot@example.com") == "pilot@example.com"
        user = session.get(AppUser, "pilot@example.com")
        auth_record = session.exec(select(AuthSession)).one()
        assert user.password_hash != "correct horse"
        assert token not in auth_record.session_hash
        assert authenticate(session, "other@example.com", "password", "pilot@example.com") is None
        assert authenticate(session, "pilot@example.com", "wrong", "pilot@example.com") is None
        logout(session, token)
        assert validate_session(session, token, "pilot@example.com") is None
