import asyncio

from rest_framework.request import Request
from rest_framework import exceptions


class AsyncRequest(Request):
    async def authenticate(self):
        """
        Attempt to authenticate the request using each authentication instance
        in turn.
        """
        self._authenticator, self.user, self.auth = None, None, None

        for authenticator in self.authenticators:
            if not asyncio.iscoroutinefunction(authenticator.authenticate):
                raise TypeError("'authenticate()' should be async function")

        authentication_results = await asyncio.gather(
            *(authenticator.authenticate(self) for authenticator in self.authenticators), return_exceptions=True
        )

        for idx in range(len(self.authenticators)):
            if isinstance(authentication_results[idx], exceptions.APIException):
                self._not_authenticated()
                raise authentication_results[idx]
            elif isinstance(authentication_results[idx], Exception):
                raise authentication_results[idx]

            user_auth_tuple = authentication_results[idx]

            if user_auth_tuple is not None:
                self._authenticator = self.authenticators[idx]
                self.user, self.auth = user_auth_tuple
                return
