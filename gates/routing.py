from django.urls import path
from .consumers import GateStatusConsumer

websocket_urlpatterns = [
    path('ws/gate-status/', GateStatusConsumer.as_asgi()),
]
