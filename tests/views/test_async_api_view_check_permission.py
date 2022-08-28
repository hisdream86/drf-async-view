import pytest

from django.http import HttpRequest
from http import HTTPStatus
from pytest_mock import MockerFixture
from rest_framework.exceptions import PermissionDenied
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer

from drfasyncview import AsyncRequest, AsyncAPIView
from tests.utils import (
    AsyncAuthenticatorReturnsAuthTuple,
    AsyncPermission,
    AsyncPermissionDenied,
    AsyncThrottle,
    SyncPermission,
    SyncPermissionDenied,
    TestVersioning,
)


class MyTestAsyncAPIView(AsyncAPIView):
    authentication_classes = [AsyncAuthenticatorReturnsAuthTuple]
    permission_classes = [AsyncPermission]
    parser_classes = [JSONParser]
    renderer_classes = [JSONRenderer]
    throttle_classes = [AsyncThrottle]
    content_negotiation_class = DefaultContentNegotiation
    versioning_class = TestVersioning


@pytest.mark.asyncio
async def test_async_check_permission(request: AsyncRequest, mocker: MockerFixture):
    async def _side_effect(self, request: AsyncRequest, view: AsyncAPIView) -> bool:
        request.has_permission_called = True
        return True

    view = MyTestAsyncAPIView()
    view.permission_classes = [AsyncPermission]
    request = view.initialize_request(HttpRequest())

    mocker.patch("tests.utils.AsyncPermission.has_permission", _side_effect)

    assert await view.check_permissions(request) is None
    assert request.has_permission_called is True


@pytest.mark.asyncio
async def test_async_check_permission_with_permission_denied():
    view = MyTestAsyncAPIView()
    view.permission_classes = [AsyncPermissionDenied]
    request = view.initialize_request(HttpRequest())

    with pytest.raises(PermissionDenied) as exc_info:
        await request.authenticate()
        await view.check_permissions(request)
    assert str(exc_info.value) == "You do not have permission to perform this action."
    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_async_check_permission_with_unexpected_error(mocker: MockerFixture):
    async def _side_effect(self, request: AsyncRequest, view: AsyncAPIView) -> bool:
        raise Exception("Test Exception")

    view = MyTestAsyncAPIView()
    view.permission_classes = [AsyncPermission]
    request = view.initialize_request(HttpRequest())

    mocker.patch("tests.utils.AsyncPermission.has_permission", _side_effect)

    with pytest.raises(Exception) as exc_info:
        await request.authenticate()
        await view.check_permissions(request)
    assert str(exc_info.value) == "Test Exception"


@pytest.mark.asyncio
async def test_sync_check_permission(request: AsyncRequest, mocker: MockerFixture):
    def _side_effect(self, request: AsyncRequest, view: AsyncAPIView) -> bool:
        request.has_permission_called = True
        return True

    view = MyTestAsyncAPIView()
    view.permission_classes = [SyncPermission]
    request = view.initialize_request(HttpRequest())

    mocker.patch("tests.utils.SyncPermission.has_permission", _side_effect)

    assert await view.check_permissions(request) is None
    assert request.has_permission_called is True


@pytest.mark.asyncio
async def test_sync_check_permission_with_permission_denied(request: AsyncRequest, mocker: MockerFixture):
    view = MyTestAsyncAPIView()
    view.permission_classes = [SyncPermission, SyncPermissionDenied]
    request = view.initialize_request(HttpRequest())

    with pytest.raises(PermissionDenied) as exc_info:
        await request.authenticate()
        await view.check_permissions(request)
    assert str(exc_info.value) == "You do not have permission to perform this action."
    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_sync_check_permission_with_unexpected_error(mocker: MockerFixture):
    def _side_effect(self, request: AsyncRequest, view: AsyncAPIView) -> bool:
        raise Exception("Test Exception")

    view = MyTestAsyncAPIView()
    view.permission_classes = [SyncPermission]
    request = view.initialize_request(HttpRequest())

    mocker.patch("tests.utils.SyncPermission.has_permission", _side_effect)

    with pytest.raises(Exception) as exc_info:
        await request.authenticate()
        await view.check_permissions(request)
    assert str(exc_info.value) == "Test Exception"


@pytest.mark.asyncio
async def test_check_permission_with_hybrid_permissions(request: AsyncRequest, mocker: MockerFixture):
    async def _side_effect_async_permission(self, request: AsyncRequest, view: AsyncAPIView) -> bool:
        request.has_async_permission_called = True
        return True

    def _side_effect_sync_permission(self, request: AsyncRequest, view: AsyncAPIView) -> bool:
        request.has_sync_permission_called = True
        return True

    view = MyTestAsyncAPIView()
    view.permission_classes = [AsyncPermission, SyncPermission]

    mocker.patch("tests.utils.AsyncPermission.has_permission", _side_effect_async_permission)
    mocker.patch("tests.utils.SyncPermission.has_permission", _side_effect_sync_permission)

    assert await view.check_permissions(request) is None
    assert request.has_async_permission_called is True
    assert request.has_sync_permission_called is True


@pytest.mark.asyncio
async def test_check_permission_with_empty_permissions(request: AsyncRequest):
    view = MyTestAsyncAPIView()
    view.permission_classes = []
    assert await view.check_permissions(request) is None
