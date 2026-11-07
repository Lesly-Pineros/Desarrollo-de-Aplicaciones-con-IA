"""HTTP-independent application service: no financial logic lives in the browser."""

from __future__ import annotations

from dataclasses import asdict
import logging
import threading
import re
from time import perf_counter

from sqlmodel import Session

from investiq.conversation import answer_turn, start_guided_exploration
from investiq.domain import ConversationState
from investiq.instruments import INSTRUMENTS
from investiq.logging_config import log_stage
from investiq.memory import forget_memory, load_memory, set_memory_enabled
from investiq.settings import Settings
from investiq.web.sessions import BrowserSession

LOCAL_USER_ID = "local"
MAX_VISIBLE_MESSAGES = 80
logger = logging.getLogger(__name__)


class InvalidRequest(ValueError):
    """A user-facing validation error with no internal data."""


class WebService:
    def __init__(self, engine, settings: Settings):
        self.engine = engine
        self.settings = settings
        # Preferences and sanitized recall intentionally share one local profile.
        # Serialize its writes across browser sessions to avoid SQLite upsert races.
        self._profile_lock = threading.RLock()
        self._context_version = 0

    def _memory(self, db: Session) -> dict:
        snapshot = load_memory(db, LOCAL_USER_ID, self.settings.conversation_memory_days)
        return {"enabled": snapshot.enabled, "summary": snapshot.summary}

    def _state(self, db: Session, browser: BrowserSession) -> ConversationState:
        if browser.context_version != self._context_version:
            # Another window may have forgotten the shared local context.
            # Never let its cached state put that forgotten summary back in DB.
            browser.state = None
            browser.messages.clear()
            browser.context_version = self._context_version
        if browser.state is None:
            browser.state = load_memory(db, LOCAL_USER_ID,
                                        self.settings.conversation_memory_days).state
        return browser.state

    def _context_cleared(self, browser: BrowserSession) -> None:
        """Invalidate cached context in other windows under the profile lock."""
        self._context_version += 1
        browser.context_version = self._context_version
        browser.messages.clear()

    def bootstrap(self, browser: BrowserSession) -> dict:
        with log_stage(logger, "service.bootstrap"), self._profile_lock, Session(self.engine) as db:
            self._state(db, browser)
            return {
                "instruments": [asdict(item) for item in INSTRUMENTS],
                "messages": list(browser.messages),
                "memory": self._memory(db),
                "mode": "configured" if self.settings.has_nvidia_key else "local",
            }

    def chat(self, browser: BrowserSession, payload: dict) -> dict:
        if payload == {"action": "start_recommendations"}:
            started = perf_counter()
            logger.info("chat.start_recommendations mode=%s",
                        "configured" if self.settings.has_nvidia_key else "local")
            with self._profile_lock, Session(self.engine) as db:
                with log_stage(logger, "service.restore_state"):
                    state = self._state(db, browser).model_copy(deep=True)
                with log_stage(logger, "service.dialogue"):
                    response = start_guided_exploration(db, LOCAL_USER_ID, self.settings, state=state)
                browser.state = state
                serialized = response.model_dump(mode="json")
                browser.messages.append({
                    "role": "assistant", "content": response.answer,
                    "sources": serialized["sources"], "status": response.status,
                    "actions": serialized["actions"],
                })
                del browser.messages[:-MAX_VISIBLE_MESSAGES]
                logger.info("chat.done intent=%s status=%s duration_ms=%d tools=%s",
                            response.intent, response.status,
                            round((perf_counter() - started) * 1000),
                            ",".join(response.tools_used) or "none")
                return {"response": serialized, "memory": self._memory(db)}
        if (set(payload) not in ({"message"}, {"message", "news_id"})
                or not isinstance(payload.get("message"), str)):
            raise InvalidRequest("Envía un mensaje de texto para continuar.")
        if "news_id" in payload and (not isinstance(payload["news_id"], str)
                or not re.fullmatch(r"news:[a-z0-9:-]{1,94}", payload["news_id"])):
            raise InvalidRequest("Elige una noticia del listado para continuar.")
        message = payload["message"].strip()
        if not message:
            raise InvalidRequest("Escribe lo que te gustaría preguntar.")
        try:
            message.encode("utf-8")
        except UnicodeEncodeError:
            raise InvalidRequest("No pude leer algunos caracteres. Vuelve a escribir el mensaje.") from None
        if len(payload["message"]) > 2000:
            raise InvalidRequest("Tu mensaje es muy largo. Puedes dividirlo en mensajes de hasta 2000 caracteres.")
        started = perf_counter()
        logger.info("chat.start mode=%s", "configured" if self.settings.has_nvidia_key else "local")
        with self._profile_lock, Session(self.engine) as db:
            # Preserve the prior temporary state if an unexpected provider/DB error escapes.
            with log_stage(logger, "service.restore_state"):
                state = self._state(db, browser).model_copy(deep=True)
            selection = {"news_selection_id": payload["news_id"]} if "news_id" in payload else {}
            with log_stage(logger, "service.dialogue"):
                response = answer_turn(db, LOCAL_USER_ID, message, self.settings, state=state, **selection)
            browser.state = state
            with log_stage(logger, "service.persist_response"):
                serialized = response.model_dump(mode="json")
            if response.clear_history:
                self._context_cleared(browser)
            else:
                browser.messages.append({"role": "user", "content": message})
            browser.messages.append({
                "role": "assistant", "content": response.answer,
                "sources": serialized["sources"], "status": response.status,
                "actions": serialized["actions"],
            })
            del browser.messages[:-MAX_VISIBLE_MESSAGES]
            logger.info("chat.done intent=%s status=%s duration_ms=%d tools=%s",
                        response.intent, response.status,
                        round((perf_counter() - started) * 1000),
                        ",".join(response.tools_used) or "none")
            return {"response": serialized, "memory": self._memory(db)}

    def reset(self, browser: BrowserSession, payload: dict) -> dict:
        if payload:
            raise InvalidRequest("No hacen falta datos para iniciar otra conversación.")
        with self._profile_lock, Session(self.engine) as db:
            forget_memory(db, LOCAL_USER_ID)
            browser.state = ConversationState()
            self._context_cleared(browser)
            return {"memory": self._memory(db), "messages": []}

    def memory(self, browser: BrowserSession, payload: dict) -> dict:
        with self._profile_lock, Session(self.engine) as db:
            if set(payload) == {"enabled"} and type(payload["enabled"]) is bool:
                set_memory_enabled(db, LOCAL_USER_ID, payload["enabled"])
            elif payload == {"forget": True} and type(payload["forget"]) is bool:
                forget_memory(db, LOCAL_USER_ID)
                browser.state = ConversationState()
                self._context_cleared(browser)
            else:
                raise InvalidRequest("Elige activar, desactivar u olvidar el contexto guardado.")
            result = {"memory": self._memory(db)}
            if payload.get("forget"):
                result["messages"] = []
            return result
