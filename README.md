# drf-async-view

Django supports [AsyncView](https://docs.djangoproject.com/en/4.1/releases/4.1/#asynchronous-handlers-for-class-based-views) from 4.1 to support writing asynchronous handlers.

`AsyncAPIView` allows you to use async handlers keeping the compatibility with django-rest-framework as well.

## Installation

You can install the latest release from pypi:

```sh
$ pip install drfasyncview
```

## How to use

### Example

```python
import asyncio

from django.contrib.auth.models import User
from django.db import models
from django.http import HttpRequest, JsonResponse
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.throttling import BaseThrottle
from typing import Optional, Tuple

from drfasyncview import AsyncRequest, AsyncAPIView


class AsyncAuthentication(BaseAuthentication):    
    async def authenticate(self, request: AsyncRequest) -> Optional[Tuple[User, str]]:
        await asyncio.sleep(0.01)
        return None


class AsyncPermission(BasePermission):
    async def has_permission(self, request: AsyncRequest, view: AsyncAPIView) -> bool:
        await asyncio.sleep(0.01)
        return True


class AsyncThrottle(BaseThrottle):
    async def allow_request(self, request: AsyncRequest, view: AsyncAPIView) -> bool:
        await asyncio.sleep(0.01)
        return True


class Product(models.Model):
    name = models.CharField(max_length=256, unique=True)
    price = models.IntegerField()


class ProductsView(AsyncAPIView):
    authentication_classes = [AsyncAuthentication]
    permission_classes = [AsyncPermission]
    throttle_classes = [AsyncThrottle]

    async def post(self, request: HttpRequest) -> JsonResponse:
        name = request.data["name"]
        price = request.data["price"]

        product = await Product.objects.acreate(name=name, price=price)

        return JsonResponse(
            data={"name": product.name, "price": product.price},
            status=200,
        )
```
