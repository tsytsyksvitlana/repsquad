"""Pieces shared by the route modules."""
from typing import NamedTuple

from fastapi import Header

from ..services import RepSquad


class Session(NamedTuple):
    user_id: int
    token: str


def dump(model):
    """Only the fields the client actually sent (absent fields keep their defaults in the domain layer)."""
    return model.model_dump(exclude_unset=True)


def make_current(service: RepSquad):
    def current(authorization: str | None = Header(default=None)) -> Session:
        """Bearer-token dependency: resolves the signed-in user or raises Unauthorized (401)."""
        token = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else None
        return Session(service.authenticate(token), token)
    return current
