import json

from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from . import services
from .models import Patient


def home(request):
    return render(request, "clinic_queue/home.html")


def reception(request):
    return render(request, "clinic_queue/reception.html")


def waiting_room(request):
    return render(request, "clinic_queue/waiting_room.html")


def get_token(request):
    return render(request, "clinic_queue/get_token.html")


def track_token(request, token_number):
    return render(
        request,
        "clinic_queue/track.html",
        {"token_number": token_number},
    )


@require_GET
def api_state(request):
    track = request.GET.get("token")
    track_token = int(track) if track and track.isdigit() else None
    return JsonResponse(services.build_queue_state(track_token=track_token))


@require_GET
def api_stream(request):
    track = request.GET.get("token")
    track_token = int(track) if track and track.isdigit() else None
    response = StreamingHttpResponse(
        services.stream_events(track_token=track_token),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@csrf_exempt
@require_http_methods(["POST"])
def api_add_patient(request):
    try:
        payload = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        payload = request.POST

    name = payload.get("name", "")
    patient = services.add_patient(name)
    return JsonResponse(
        {
            "ok": True,
            "patient": services.serialize_patient(patient),
            "state": services.build_queue_state(),
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def api_call_next(request):
    patient = services.call_next()
    return JsonResponse(
        {
            "ok": True,
            "called": services.serialize_patient(patient) if patient else None,
            "state": services.build_queue_state(),
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def api_skip(request, patient_id):
    patient = services.skip_token(patient_id)
    return JsonResponse(
        {
            "ok": True,
            "patient": services.serialize_patient(patient),
            "state": services.build_queue_state(),
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def api_recall(request, patient_id):
    patient = services.recall_token(patient_id)
    return JsonResponse(
        {
            "ok": True,
            "patient": services.serialize_patient(patient),
            "state": services.build_queue_state(),
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def api_settings(request):
    try:
        payload = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        payload = request.POST

    minutes = payload.get("avg_consultation_minutes", 10)
    settings = services.set_avg_consultation_minutes(minutes)
    return JsonResponse(
        {
            "ok": True,
            "avg_consultation_minutes": settings.avg_consultation_minutes,
            "state": services.build_queue_state(),
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def api_reset_day(request):
    Patient.objects.filter(queue_date=services.today()).delete()
    services.bump_state()
    return JsonResponse({"ok": True, "state": services.build_queue_state()})
