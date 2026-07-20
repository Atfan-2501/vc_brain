"""Per-user scoping. The frontend proxy forwards the logged-in Supabase user id as the
`X-User-Id` header. We stash it in a request-scoped context var so db.py can stamp owner_id on
writes and filter reads — without threading a user id through every function signature.

Background tasks don't inherit the request context, so capture the id in the endpoint and run
the task via run_as_user()."""
import contextvars
from fastapi import Header, HTTPException

import config

_current_user: contextvars.ContextVar = contextvars.ContextVar("current_user", default=None)


def current_user_id():
    return _current_user.get()


def set_user(uid):
    _current_user.set(uid)


async def require_user(x_user_id: str = Header(default=None)):
    """FastAPI dependency for data endpoints. Sets the context and returns the user id.
    Async so the contextvar it sets propagates to the (sync) endpoint handlers.
    When AUTH_REQUIRED is off (single-tenant/dev), a missing header is allowed (owner=None)."""
    if x_user_id:
        _current_user.set(x_user_id)
        return x_user_id
    if config.AUTH_REQUIRED:
        raise HTTPException(401, "missing X-User-Id header")
    _current_user.set(None)
    return None


def run_as_user(uid, fn, *args, **kwargs):
    """Wrap a background task so it runs under the capturing request's user."""
    _current_user.set(uid)
    return fn(*args, **kwargs)
