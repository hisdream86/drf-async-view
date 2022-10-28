import asyncio

from django.http import HttpRequest, HttpResponse
from typing import Iterable, Generator, AsyncGenerator
from rest_framework.views import APIView
from rest_framework import exceptions
from rest_framework.permissions import BasePermission
from rest_framework.throttling import BaseThrottle
from http import HTTPStatus

from drfasyncview.requests import AsyncRequest


class AsyncAPIView(APIView):
    def initialize_request(self, request, *args, **kwargs) -> AsyncRequest:
        """
        Returns the initial request object.
        """
        parser_context = self.get_parser_context(request)

        return AsyncRequest(
            request,
            parsers=self.get_parsers(),
            authenticators=self.get_authenticators(),
            negotiator=self.get_content_negotiator(),
            parser_context=parser_context,
        )

    async def initial(self, request: AsyncRequest, *args, **kwargs) -> None:
        """
        `.dispatch()` is pretty much the same as Django's regular dispatch,
        but with extra hooks for startup, finalize, and exception handling.
        """
        self.format_kwarg = self.get_format_suffix(**kwargs)

        # Perform content negotiation and store the accepted info on the request
        neg = self.perform_content_negotiation(request)
        request.accepted_renderer, request.accepted_media_type = neg

        # Determine the API version, if versioning is in use.
        version, scheme = self.determine_version(request, *args, **kwargs)
        request.version, request.versioning_scheme = version, scheme

        # Ensure that the incoming request is permitted
        await request.authenticate()
        await self.check_permissions(request)
        await self.check_throttles(request)

    def _check_sync_permissions(self, request: AsyncRequest, permissions: Iterable[BasePermission]):
        for permission in permissions:
            if not permission.has_permission(request, self):
                self.permission_denied(
                    request, message=getattr(permission, "message", None), code=getattr(permission, "code", None)
                )

    async def _check_async_permissions(self, request: AsyncRequest, permissions: Iterable[BasePermission]):
        results = await asyncio.gather(
            *(permission.has_permission(request, self) for permission in permissions), return_exceptions=True
        )

        for idx in range(len(permissions)):
            if isinstance(results[idx], Exception):
                raise results[idx]
            elif not results[idx]:
                self.permission_denied(
                    request,
                    message=getattr(permissions[idx], "message", None),
                    code=getattr(permissions[idx], "code", None),
                )

    async def check_permissions(self, request: AsyncRequest) -> None:
        """
        Check if the request should be permitted.
        Raises an appropriate exception if the request is not permitted.
        """
        permissions = self.get_permissions()

        async_permissions, sync_permissions = [], []

        for permission in permissions:
            if asyncio.iscoroutinefunction(permission.has_permission):
                async_permissions.append(permission)
            else:
                sync_permissions.append(permission)

        self._check_sync_permissions(request, sync_permissions)
        await self._check_async_permissions(request, async_permissions)

    def _check_sync_throttles(
        self, request: AsyncRequest, throttles: Iterable[BaseThrottle]
    ) -> Generator[float, None, None]:
        for throttle in throttles:
            if not throttle.allow_request(request, self):
                yield throttle.wait()

    async def _check_async_throttles(
        self, request: AsyncRequest, throttles: Iterable[BaseThrottle]
    ) -> AsyncGenerator[float, None]:
        for throttle in throttles:
            if not await throttle.allow_request(request, self):
                yield throttle.wait()

    async def check_throttles(self, request: AsyncRequest) -> None:
        """
        Check if request should be throttled.
        Raises an appropriate exception if the request is throttled.
        """
        throttle_durations = []
        throttles = self.get_throttles()
        async_throttles = filter(lambda t: asyncio.iscoroutinefunction(t.allow_request), throttles)
        sync_throttles = filter(lambda t: not asyncio.iscoroutinefunction(t.allow_request), throttles)

        throttle_durations.extend(self._check_sync_throttles(request, sync_throttles))
        throttle_durations.extend(
            [duration async for duration in self._check_async_throttles(request, async_throttles)]
        )

        if throttle_durations:
            durations = [duration for duration in throttle_durations if duration is not None]
            duration = max(durations, default=None)
            self.throttled(request, duration)

    async def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        # Note: Views are made CSRF exempt from within `as_view` as to prevent
        # accidental removal of this exemption in cases where `dispatch` needs to
        # be overridden.
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers  # deprecate?

        try:
            await self.initial(request, *args, **kwargs)

            # Get the appropriate handler method
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(), None)
            else:
                handler = None

            if handler is None:
                raise exceptions.MethodNotAllowed(request.method)

            if asyncio.iscoroutinefunction(handler):
                response = await handler(request, *args, **kwargs)
            else:
                raise TypeError("Handler should be async function")

        except Exception as exc:
            response = await self.handle_exception(exc)

        self.response = self.finalize_response(request, response, *args, **kwargs)

        return self.response

    async def handle_exception(self, exc: Exception):
        """
        Handle any exception that occurs, by returning an appropriate response,
        or re-raising the error.
        """
        if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
            # WWW-Authenticate header for 401 responses, else coerce to 403
            auth_header = self.get_authenticate_header(self.request)

            if auth_header:
                exc.auth_header = auth_header
            else:
                exc.status_code = HTTPStatus.FORBIDDEN

        exception_handler = self.get_exception_handler()

        context = self.get_exception_handler_context()

        response = exception_handler(exc, context)

        if response is None:
            self.raise_uncaught_exception(exc)

        response.exception = True
        return response
