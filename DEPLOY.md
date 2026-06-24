# Deploy for online hackathon (Render — free)

Judges need a **public URL**. Local `runserver` is not enough for online judging.

## 5-step deploy (about 15 minutes)

### 1. Push code to GitHub

```bash
cd clinic-queue-manager
git init
git add .
git commit -m "Clinic queue manager for hackathon"
```

Create a new repo on GitHub, then:

```bash
git remote add origin https://github.com/YOUR_USERNAME/clinic-queue-manager.git
git branch -M main
git push -u origin main
```

### 2. Create Render account

Go to [render.com](https://render.com) → sign up with GitHub.

### 3. New Web Service

- **New +** → **Web Service**
- Connect your GitHub repo
- Render auto-detects `render.yaml` OR set manually:
  - **Build command:** `./build.sh`
  - **Start command:** `gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
  - **Plan:** Free

### 4. Wait for deploy (~3–5 min)

Your URL will look like:

`https://clinic-queue-manager.onrender.com`

### 5. Test before submitting

| Screen | URL |
|--------|-----|
| Home | `https://YOUR-APP.onrender.com/` |
| Reception | `https://YOUR-APP.onrender.com/reception/` |
| Get token | `https://YOUR-APP.onrender.com/get-token/` |
| Waiting room | `https://YOUR-APP.onrender.com/waiting-room/` |

Open **Get token** on your phone and **Reception** on laptop → click **Call next** → phone should update live.

---

## What to put in your hackathon submission

```
Live demo:  https://clinic-queue-manager.onrender.com
Reception:  https://clinic-queue-manager.onrender.com/reception/
Patient:    https://clinic-queue-manager.onrender.com/get-token/
```

Add a 30–60 sec screen recording as backup (free tier may sleep after ~15 min idle).

---

## Free tier notes

- First load after idle can take **30–60 seconds** (cold start) — open the site 2 min before your pitch
- SQLite resets if Render redeploys — fine for demo; add patients fresh each time
- Keep a **local backup** (`run.bat`) if live URL fails during Q&A
