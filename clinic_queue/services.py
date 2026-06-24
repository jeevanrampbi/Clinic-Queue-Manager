import json
import threading

from django.db.models import Avg, ExpressionWrapper, DurationField, F
from django.utils import timezone

from .models import ClinicSettings, Patient

_state_lock = threading.Lock()
_state_version = 0
_listeners: list[threading.Event] = []


def bump_state():
    global _state_version
    with _state_lock:
        _state_version += 1
        for event in _listeners:
            event.set()


def register_listener():
    event = threading.Event()
    with _state_lock:
        _listeners.append(event)
    return event


def unregister_listener(event):
    with _state_lock:
        if event in _listeners:
            _listeners.remove(event)


def current_version():
    with _state_lock:
        return _state_version


def today():
    return timezone.localdate()


def patients_today():
    return Patient.objects.filter(queue_date=today())


def next_token_number():
    last = patients_today().order_by("-token_number").first()
    return (last.token_number + 1) if last else 1


def add_patient(name, source="reception"):
    name = (name or "").strip() or f"Walk-in {next_token_number()}"
    patient = Patient.objects.create(
        token_number=next_token_number(),
        name=name,
        queue_date=today(),
    )
    bump_state()
    return patient


def call_next():
    current = patients_today().filter(status=Patient.STATUS_IN_CONSULTATION).first()
    if current:
        current.status = Patient.STATUS_COMPLETED
        current.completed_at = timezone.now()
        current.save(update_fields=["status", "completed_at"])

    nxt = patients_today().filter(status=Patient.STATUS_WAITING).order_by("token_number").first()
    if not nxt:
        bump_state()
        return None

    nxt.status = Patient.STATUS_IN_CONSULTATION
    nxt.called_at = timezone.now()
    nxt.save(update_fields=["status", "called_at"])
    bump_state()
    return nxt


def skip_token(patient_id):
    patient = patients_today().get(pk=patient_id)
    if patient.status != Patient.STATUS_WAITING:
        return patient
    patient.status = Patient.STATUS_SKIPPED
    patient.save(update_fields=["status"])
    bump_state()
    return patient


def recall_token(patient_id):
    patient = patients_today().get(pk=patient_id)
    if patient.status not in (Patient.STATUS_SKIPPED, Patient.STATUS_COMPLETED):
        return patient
    patient.status = Patient.STATUS_WAITING
    patient.called_at = None
    patient.completed_at = None
    patient.save(update_fields=["status", "called_at", "completed_at"])
    bump_state()
    return patient


def set_avg_consultation_minutes(minutes):
    settings = ClinicSettings.get_solo()
    settings.avg_consultation_minutes = max(1, int(minutes))
    settings.save(update_fields=["avg_consultation_minutes", "updated_at"])
    bump_state()
    return settings


def measured_avg_minutes():
    completed = patients_today().filter(
        status=Patient.STATUS_COMPLETED,
        called_at__isnull=False,
        completed_at__isnull=False,
    )
    if completed.count() < 2:
        return None

    avg_duration = completed.annotate(
        duration=ExpressionWrapper(
            F("completed_at") - F("called_at"),
            output_field=DurationField(),
        )
    ).aggregate(avg=Avg("duration"))["avg"]

    if not avg_duration:
        return None
    return max(1, round(avg_duration.total_seconds() / 60))


def effective_avg_minutes():
    measured = measured_avg_minutes()
    if measured is not None:
        return measured
    return ClinicSettings.get_solo().avg_consultation_minutes


def patients_ahead(token_number):
    current = patients_today().filter(status=Patient.STATUS_IN_CONSULTATION).first()
    ahead = patients_today().filter(
        status=Patient.STATUS_WAITING,
        token_number__lt=token_number,
    ).count()
    if current and token_number > current.token_number:
        return ahead
    if current and token_number == current.token_number:
        return 0
    return ahead


def estimated_wait_minutes(token_number=None):
    avg = effective_avg_minutes()
    if token_number is None:
        waiting_count = patients_today().filter(status=Patient.STATUS_WAITING).count()
        return waiting_count * avg

    ahead = patients_ahead(token_number)
    patient = patients_today().filter(token_number=token_number).first()
    if not patient or patient.status != Patient.STATUS_WAITING:
        return 0
    return ahead * avg


def serialize_patient(patient):
    return {
        "id": patient.id,
        "token_number": patient.token_number,
        "name": patient.name,
        "status": patient.status,
        "created_at": patient.created_at.isoformat(),
        "called_at": patient.called_at.isoformat() if patient.called_at else None,
        "completed_at": patient.completed_at.isoformat() if patient.completed_at else None,
        "patients_ahead": patients_ahead(patient.token_number),
        "estimated_wait_minutes": estimated_wait_minutes(patient.token_number),
    }


def build_queue_state(track_token=None):
    settings = ClinicSettings.get_solo()
    today_patients = list(patients_today())
    current = next(
        (p for p in today_patients if p.status == Patient.STATUS_IN_CONSULTATION),
        None,
    )
    waiting = [p for p in today_patients if p.status == Patient.STATUS_WAITING]
    measured = measured_avg_minutes()
    avg = effective_avg_minutes()

    active_queue = [
        p for p in today_patients
        if p.status in (Patient.STATUS_WAITING, Patient.STATUS_IN_CONSULTATION)
    ]

    tracked = None
    if track_token is not None:
        patient = patients_today().filter(token_number=track_token).first()
        if patient:
            tracked = serialize_patient(patient)

    return {
        "version": current_version(),
        "clinic_name": settings.clinic_name,
        "queue_date": today().isoformat(),
        "current_token": current.token_number if current else None,
        "current_patient_name": current.name if current else None,
        "waiting_count": len(waiting),
        "avg_consultation_minutes": settings.avg_consultation_minutes,
        "measured_avg_minutes": measured,
        "effective_avg_minutes": avg,
        "wait_source": "measured" if measured is not None else "configured",
        "estimated_wait_minutes": estimated_wait_minutes(track_token),
        "next_tokens": [p.token_number for p in waiting[:5]],
        "waiting_queue": [serialize_patient(p) for p in waiting],
        "active_queue": [serialize_patient(p) for p in active_queue],
        "recent_completed": [
            serialize_patient(p)
            for p in today_patients
            if p.status in (Patient.STATUS_COMPLETED, Patient.STATUS_SKIPPED)
        ][-5:],
        "tracked_patient": tracked,
    }


def stream_events(track_token=None):
    last_version = -1
    listener = register_listener()
    try:
        yield ": connected\n\n"
        while True:
            state = build_queue_state(track_token=track_token)
            if state["version"] != last_version:
                last_version = state["version"]
                yield f"data: {json.dumps(state)}\n\n"
            listener.wait(timeout=15)
            listener.clear()
            if listener.is_set():
                continue
            yield ": keepalive\n\n"
    finally:
        unregister_listener(listener)
