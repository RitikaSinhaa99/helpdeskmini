from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TicketViewSet, list_agents

router = DefaultRouter()
router.register(r'tickets', TicketViewSet, basename='ticket')

urlpatterns = [
    path('', include(router.urls)),
    path('users/', list_agents, name='list_agents'),
]