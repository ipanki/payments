from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.settings import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(x_api_key: str | None = Security(api_key_header)) -> None:
    if x_api_key != settings.app.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
