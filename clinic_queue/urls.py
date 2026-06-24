from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("reception/", views.reception, name="reception"),
    path("waiting-room/", views.waiting_room, name="waiting_room"),
    path("get-token/", views.get_token, name="get_token"),
    path("track/<int:token_number>/", views.track_token, name="track_token"),
    path("api/state/", views.api_state, name="api_state"),
    path("api/stream/", views.api_stream, name="api_stream"),
    path("api/patients/", views.api_add_patient, name="api_add_patient"),
    path("api/call-next/", views.api_call_next, name="api_call_next"),
    path("api/patients/<int:patient_id>/skip/", views.api_skip, name="api_skip"),
    path("api/patients/<int:patient_id>/recall/", views.api_recall, name="api_recall"),
    path("api/settings/", views.api_settings, name="api_settings"),
    path("api/reset-day/", views.api_reset_day, name="api_reset_day"),
]
