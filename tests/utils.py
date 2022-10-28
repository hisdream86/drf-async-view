import asyncio

from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.throttling import BaseThrottle
from rest_framework.versioning import BaseVersioning
from typing import Optional, Tuple

from drfasyncview import AsyncRequest, AsyncAPIView


"""
Authentications
"""


class AsyncAuthenticatorReturnsNone(BaseAuthentication):
    async def authenticate(self, request: AsyncRequest) -> Optional[Tuple[User, str]]:
        pass


class AsyncAuthenticatorReturnsAuthTuple(BaseAuthentication):
    async def authenticate(self, request: AsyncRequest) -> Optional[Tuple[User, str]]:
        await asyncio.sleep(0.05)
        return (User(username="test-user"), "test-token")


class AsyncAuthenticatorAuthenticationFailed(BaseAuthentication):
    async def authenticate(self, request: AsyncRequest) -> Optional[Tuple[User, str]]:
        raise AuthenticationFailed(detail="Test authentication failed")


class SyncAuthenticator(BaseAuthentication):
    def authenticate(self, request: AsyncRequest) -> Optional[Tuple[User, str]]:
        pass  # pragma: no cover


"""
Permissions
"""


class SyncPermission(BasePermission):
    def has_permission(self, request: AsyncRequest, view: AsyncAPIView):
        return True


class SyncPermissionDenied(BasePermission):
    def has_permission(self, request: AsyncRequest, view: AsyncAPIView):
        return False


class AsyncPermission(BasePermission):
    async def has_permission(self, request: AsyncRequest, view: AsyncAPIView):
        await asyncio.sleep(0.01)
        return True


class AsyncPermissionDenied(BasePermission):
    async def has_permission(self, request: AsyncRequest, view: AsyncAPIView):
        await asyncio.sleep(0.01)
        return False


"""
Throttle
"""


class SyncThrottle(BaseThrottle):
    def allow_request(self, request: AsyncRequest, view: AsyncAPIView) -> bool:
        return True

    def wait() -> int:
        return 999


class SyncThrottleExceeded(BaseThrottle):
    def allow_request(self, request: AsyncRequest, view: AsyncAPIView) -> bool:
        return False

    def wait(self) -> int:
        return 2


class AsyncThrottle(BaseThrottle):
    async def allow_request(self, request: AsyncRequest, view: AsyncAPIView) -> bool:
        return True


class AsyncThrottleExceeded(BaseThrottle):
    async def allow_request(self, request: AsyncRequest, view: AsyncAPIView) -> bool:
        return False

    def wait(self) -> int:
        return 3


"""
Versioning
"""


class TestVersioning(BaseVersioning):
    def determine_version(self, request, *args, **kwargs):
        return request.META.get("HTTP_X_API_VERSION", None)
