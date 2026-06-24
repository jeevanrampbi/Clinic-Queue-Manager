# Clinic Queue Manager

Live digital queue for a neighbourhood clinic — reception controls the queue, patients follow along on their phones.

## Quick start

```bash
cd clinic-queue-manager
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Open **http://127.0.0.1:8000/**

## Screens

| URL | Who uses it |
|-----|-------------|
| `/reception/` | Receptionist — add patients, call next, set avg consultation time |
| `/waiting-room/` | TV / wall display in the waiting area |
| `/get-token/` | Patients on their phone — join the queue and get a token |
| `/track/12/` | Patient bookmark — live status for token #12 |

## Demo flow (the "I want this" moment)

1. Open **Get a Token** on your phone and join as a patient.
2. Open **Reception** on the desk and add two more patients.
3. Click **Call next token** — watch your phone update instantly: token changes, patients-ahead drops, wait time recalculates.
4. After 2+ visits complete, wait times switch from configured average to **today's measured average**.

## Answers to the three questions

1. **Can reception add a patient in under 10 seconds?** Yes — type name (optional), press Enter or click Add. Token is assigned automatically.
2. **Does the patient screen update live?** Yes — Server-Sent Events push updates instantly; no page refresh.
3. **Is wait time from real data?** Yes — `patients ahead × effective average`, where effective average uses measured visit durations from today once 2+ consultations are completed; otherwise the receptionist's configured average.

## Tech

- Django 6 + SQLite
- Live sync via SSE (`/api/stream/`)
- REST JSON API under `/api/`
