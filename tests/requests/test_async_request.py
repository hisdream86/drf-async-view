import pytest

from django.http import HttpRequest
from django.contrib.auth.models import User, AnonymousUser
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from typing import Optional, Tuple

from drfasyncview.requests import AsyncRequest
from tests.utils import (
    AsyncAuthenticatorReturnsNone,
    AsyncAuthenticatorReturnsAuthTuple,
    AsyncAuthenticatorAuthenticationFailed,
    SyncAuthenticator,
)


class AsyncAuthenticatorUnexpectedException(BaseAuthentication):
    async def authenticate(self, request: AsyncRequest) -> Optional[Tuple[User, str]]:
        raise Exception("Test error")


@pytest.mark.asyncio
async def test_async_authenticate():
    async_request = AsyncRequest(
        HttpRequest(),
        parsers=[],
        authenticators=[AsyncAuthenticatorReturnsNone()],
        negotiator=[],
        parser_context={},
    )

    await async_request.authenticate()

    assert isinstance(async_request.user, AnonymousUser)
    assert async_request.auth is None
    assert async_request._authenticator is None


@pytest.mark.asyncio
async def test_async_authenticate_returns_auth_tuple():
    async_request = AsyncRequest(
        HttpRequest(),
        parsers=[],
        authenticators=[AsyncAuthenticatorReturnsAuthTuple()],
        negotiator=[],
        parser_context={},
    )

    await async_request.authenticate()

    assert async_request.user.username == "test-user"
    assert async_request.auth == "test-token"
    assert isinstance(async_request._authenticator, AsyncAuthenticatorReturnsAuthTuple)


@pytest.mark.asyncio
async def test_async_authenticate_authentication_failure():
    async_request = AsyncRequest(
        HttpRequest(),
        parsers=[],
        authenticators=[AsyncAuthenticatorAuthenticationFailed()],
        negotiator=[],
        parser_context={},
    )

    with pytest.raises(AuthenticationFailed) as exc_info:
        await async_request.authenticate()

    assert str(exc_info.value) == "Test authentication failed"


@pytest.mark.asyncio
async def test_async_authenticate_with_unexpected_exception():
    async_request = AsyncRequest(
        HttpRequest(),
        parsers=[],
        authenticators=[AsyncAuthenticatorUnexpectedException()],
        negotiator=[],
        parser_context={},
    )

    with pytest.raises(Exception) as exc_info:
        await async_request.authenticate()

    assert str(exc_info.value) == "Test error"


@pytest.mark.asyncio
async def test_sync_authenticate():
    async_request = AsyncRequest(
        HttpRequest(),
        parsers=[],
        authenticators=[SyncAuthenticator()],
        negotiator=[],
        parser_context={},
    )

    await async_request.authenticate()

    assert isinstance(async_request.user, AnonymousUser)
    assert async_request.auth is None
    assert async_request._authenticator is None


@pytest.mark.asyncio
async def test_authenticate_with_hybrid_authenticators():
    async_request = AsyncRequest(
        HttpRequest(),
        parsers=[],
        authenticators=[AsyncAuthenticatorReturnsNone(), AsyncAuthenticatorReturnsAuthTuple(), SyncAuthenticator()],
        negotiator=[],
        parser_context={},
    )

    await async_request.authenticate()

    assert async_request.user.username == "test-user"
    assert async_request.auth == "test-token"
    assert isinstance(async_request._authenticator, AsyncAuthenticatorReturnsAuthTuple)
