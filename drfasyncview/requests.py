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
            try:
                if asyncio.iscoroutinefunction(authenticator.authenticate):
                    user_auth_tuple = await authenticator.authenticate(self)
                else:
                    user_auth_tuple = authenticator.authenticate(self)
            except exceptions.APIException:
                self._not_authenticated()
                raise

            if user_auth_tuple is not None:
                self._authenticator = authenticator
                self.user, self.auth = user_auth_tuple
                return

        self._not_authenticated()
