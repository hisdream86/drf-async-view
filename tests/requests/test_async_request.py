import asyncio
import pytest

from django.http import HttpRequest
from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from typing import Optional, Tuple

from drfasyncview.requests import AsyncRequest


class AsyncAuthenticatorReturnsNone(BaseAuthentication):
    async def authenticate(self, request: AsyncRequest) -> Optional[Tuple[User, str]]:
        pass


class AsyncAuthenticatorReturnsAuthTuple(BaseAuthentication):
    async def authenticate(self, request: AsyncRequest) -> Optional[Tuple[User, str]]:
        await asyncio.sleep(0.05)
        return (User(username="test-user"), "test-token")


class AsyncAuthenticatorReturnsAuthTuple2(BaseAuthentication):
    async def authenticate(self, request: AsyncRequest) -> Optional[Tuple[User, str]]:
        await asyncio.sleep(0.01)
        return (User(username="test-user-2"), "test-token-2")


class AsyncAuthenticatorAuthenticationFailed(BaseAuthentication):
    async def authenticate(self, request: AsyncRequest) -> Optional[Tuple[User, str]]:
        raise AuthenticationFailed(detail="Test authentication failed")


class AsyncAuthenticatorUnexpectedException(BaseAuthentication):
    async def authenticate(self, request: AsyncRequest) -> Optional[Tuple[User, str]]:
        raise Exception("Test error")


class SyncAuthenticator(BaseAuthentication):
    def authenticate(self, request: AsyncRequest) -> Optional[Tuple[User, str]]:
        pass


@pytest.mark.asyncio
async def test_async_request_with_authenticator_returns_none():
    async_request = AsyncRequest(
        HttpRequest(),
        parsers=[],
        authenticators=[AsyncAuthenticatorReturnsNone()],
        negotiator=[],
        parser_context={},
    )

    await async_request.authenticate()

    assert async_request.user is None
    assert async_request.auth is None
    assert async_request._authenticator is None


@pytest.mark.asyncio
async def test_async_request_with_authenticator_returns_auth_tuple():
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
async def test_async_request_with_multiple_authenticators():
    async_request = AsyncRequest(
        HttpRequest(),
        parsers=[],
        authenticators=[AsyncAuthenticatorReturnsNone(), AsyncAuthenticatorReturnsAuthTuple()],
        negotiator=[],
        parser_context={},
    )

    await async_request.authenticate()

    assert async_request.user.username == "test-user"
    assert async_request.auth == "test-token"
    assert isinstance(async_request._authenticator, AsyncAuthenticatorReturnsAuthTuple)


@pytest.mark.asyncio
async def test_async_request_with_multiple_authenticators_returns_auth_tuple():
    async_request = AsyncRequest(
        HttpRequest(),
        parsers=[],
        authenticators=[AsyncAuthenticatorReturnsAuthTuple(), AsyncAuthenticatorReturnsAuthTuple2()],
        negotiator=[],
        parser_context={},
    )

    await async_request.authenticate()

    # Take results from the prior authenticator
    assert async_request.user.username == "test-user"
    assert async_request.auth == "test-token"
    assert isinstance(async_request._authenticator, AsyncAuthenticatorReturnsAuthTuple)


@pytest.mark.asyncio
async def test_async_request_with_authentication_failure():
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
async def test_async_request_with_unexpected_exception():
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
async def test_async_request_with_sync_function():
    async_request = AsyncRequest(
        HttpRequest(),
        parsers=[],
        authenticators=[SyncAuthenticator()],
        negotiator=[],
        parser_context={},
    )

    with pytest.raises(TypeError) as exc_info:
        await async_request.authenticate()

    assert str(exc_info.value) == "'authenticate()' should be async function"
