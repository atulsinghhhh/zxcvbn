"""FastAPI dependency callables for shared clients."""

from fastapi import Request

from app.clients.fuelhh_client import FuelHHClient
from app.clients.windfor_client import WindForClient


def get_windfor_client(request: Request) -> WindForClient:
    return request.app.state.windfor_client  # type: ignore[no-any-return]


def get_fuelhh_client(request: Request) -> FuelHHClient:
    return request.app.state.fuelhh_client  # type: ignore[no-any-return]
