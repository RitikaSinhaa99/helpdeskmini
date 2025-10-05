from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("tickets/", views.tickets_page, name="tickets"),
    path("login/", views.login_page, name="login"),
]
