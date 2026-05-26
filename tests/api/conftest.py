import pytest
from dependency_injector import providers
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.router import router
from app.container import container
from app.settings import settings

container.wire(packages=["app.api"])


@pytest.fixture
def app(payment_service):
    test_app = FastAPI()
    test_app.include_router(router)

    with container.payment_service.override(providers.Object(payment_service)):
        yield test_app


@pytest.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": settings.app.api_key},
    ) as ac:
        yield ac
