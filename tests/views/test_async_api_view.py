import pytest

from django.http import HttpRequest
from http import HTTPStatus
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer

from drfasyncview import AsyncRequest, AsyncAPIView
from tests.utils import (
    AsyncAuthenticatorReturnsAuthTuple,
    AsyncAuthenticatorAuthenticationFailed,
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


def test_async_api_view_initialize_request():
    view = MyTestAsyncAPIView()
    http_request = HttpRequest()
    request = view.initialize_request(http_request)
    parser_context = view.get_parser_context(http_request)

    assert isinstance(request, AsyncRequest)
    assert isinstance(request.parsers[0], JSONParser)
    assert isinstance(request.authenticators[0], AsyncAuthenticatorReturnsAuthTuple)
    assert isinstance(request.negotiator, DefaultContentNegotiation)
    for key in parser_context:
        assert parser_context[key] == request.parser_context[key]


@pytest.mark.asyncio
async def test_async_api_view_initial():
    view = MyTestAsyncAPIView()
    request = view.initialize_request(HttpRequest())
    kwargs = {"format": "json"}
    request.META["HTTP_X_API_VERSION"] = "v1"

    await view.initial(request, **kwargs)

    renderer, media_type = view.perform_content_negotiation(request)
    version, scheme = view.determine_version(request)

    assert view.format_kwarg == view.get_format_suffix(**kwargs)
    assert type(request.accepted_renderer) == type(renderer)
    assert request.accepted_media_type == media_type
    assert version == request.META["HTTP_X_API_VERSION"]
    assert type(scheme) == TestVersioning


@pytest.mark.asyncio
async def test_async_api_view_initial_with_authentication_faiure():
    view = MyTestAsyncAPIView()
    view.authentication_classes = [AsyncAuthenticatorAuthenticationFailed]

    with pytest.raises(AuthenticationFailed) as exc_info:
        await view.initial(view.initialize_request(HttpRequest()))
    assert str(exc_info.value) == "Test authentication failed"
    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_async_api_view_initial_with_throttled():
    view = MyTestAsyncAPIView()
    view.throttle_classes = [AsyncThrottleExceeded]
    wait = AsyncThrottleExceeded().wait()

    with pytest.raises(Throttled) as exc_info:
        await view.initial(view.initialize_request(HttpRequest()))
    assert str(exc_info.value) == f"Request was throttled. Expected available in {wait} seconds."
    assert exc_info.value.status_code == HTTPStatus.TOO_MANY_REQUESTS
