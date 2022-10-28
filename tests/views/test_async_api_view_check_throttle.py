import pytest

from django.http import HttpRequest
from http import HTTPStatus
from pytest_mock import MockerFixture
from rest_framework.exceptions import Throttled
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer

from drfasyncview import AsyncRequest, AsyncAPIView
from tests.utils import (
    AsyncAuthenticatorReturnsAuthTuple,
    AsyncPermission,
    AsyncThrottle,
    AsyncThrottleExceeded,
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
async def test_async_check_throttle(request: AsyncRequest, mocker: MockerFixture):
    async def _side_effect(self, request: AsyncRequest, view: AsyncAPIView) -> bool:
        request.allow_request_called = True
        return True

    view = MyTestAsyncAPIView()
    view.throttle_classes = [AsyncThrottle]
    request = view.initialize_request(HttpRequest())

    mocker.patch("tests.utils.AsyncThrottle.allow_request", _side_effect)

    assert await view.check_throttles(request) is None
    assert request.allow_request_called is True


@pytest.mark.asyncio
async def test_async_check_throttle_with_throttled(request: AsyncRequest, mocker: MockerFixture):
    view = MyTestAsyncAPIView()
    view.throttle_classes = [AsyncThrottleExceeded]
    request = view.initialize_request(HttpRequest())
    wait = AsyncThrottleExceeded().wait()

    mocker.patch("tests.utils.AsyncThrottle.allow_request", return_value=False)

    with pytest.raises(Throttled) as exc_info:
        await view.check_throttles(request)
    assert str(exc_info.value) == f"Request was throttled. Expected available in {wait} second."
    assert exc_info.value.status_code == HTTPStatus.TOO_MANY_REQUESTS


@pytest.mark.asyncio
async def test_async_check_throttle_with_unexpected_error(mocker: MockerFixture):
    async def _side_effect(self, request: AsyncRequest, view: AsyncAPIView) -> bool:
        raise Exception("Test Exception")

    view = MyTestAsyncAPIView()
    view.throttle_classes = [AsyncThrottle]
    request = view.initialize_request(HttpRequest())

    mocker.patch("tests.utils.AsyncThrottle.allow_request", _side_effect)

    with pytest.raises(Exception) as exc_info:
        await view.check_throttles(request)
    assert str(exc_info.value) == "Test Exception"


@pytest.mark.asyncio
async def test_check_throttle_with_empty_throttles(request: AsyncRequest):
    view = MyTestAsyncAPIView()
    view.throttle_classes = []
    request = view.initialize_request(HttpRequest())

    assert await view.check_throttles(request) is None
