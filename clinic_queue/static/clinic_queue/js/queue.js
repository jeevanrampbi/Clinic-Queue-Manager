(function () {
  const page = window.QueuePage || {};
  let source = null;
  let pollTimer = null;
  let myToken = page.token || null;
  let lastVersion = -1;

  function $(id) {
    return document.getElementById(id);
  }

  function formatWait(minutes) {
    if (minutes === 0) return "Now";
    if (minutes === 1) return "1 min";
    return `${minutes} min`;
  }

  function statusLabel(status) {
    return {
      waiting: "Waiting",
      in_consultation: "In consultation",
      completed: "Completed",
      skipped: "Skipped",
    }[status] || status;
  }

  async function postJson(url, body) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    return response.json();
  }

  function applyState(state) {
    if (!state) return;
    lastVersion = state.version;
    if (page.mode === "reception") renderReception(state);
    if (page.mode === "waiting_room") renderWaitingRoom(state);
    if (page.mode === "get_token") renderGetToken(state);
    if (page.mode === "track") {
      $("your-token").textContent = `#${page.token}`;
      renderTrackedPatient(state);
      $("mini-current").textContent = state.current_token ? `#${state.current_token}` : "—";
    }
  }

  async function refreshState() {
    const params = myToken ? `?token=${myToken}` : "";
    const response = await fetch(`/api/state/${params}`.replace("/?", "?"));
    if (!response.ok) return;
    const state = await response.json();
    if (state.version !== lastVersion) {
      applyState(state);
    }
  }

  function renderReception(state) {
    $("clinic-name").textContent = state.clinic_name;
    $("current-token").textContent = state.current_token ? `#${state.current_token}` : "—";
    $("current-name").textContent = state.current_patient_name || "No patient in consultation";
    $("waiting-count").textContent = `${state.waiting_count} waiting`;
    $("avg-minutes").value = state.avg_consultation_minutes;

    const sourceText = state.wait_source === "measured"
      ? `Live average from today's visits: ${state.measured_avg_minutes} min (${state.effective_avg_minutes} min used for estimates).`
      : `Using configured average (${state.avg_consultation_minutes} min) until 2+ visits complete today.`;
    $("wait-source").textContent = sourceText;

    const list = $("queue-list");
    list.innerHTML = "";
    const items = [...(state.active_queue || []), ...(state.recent_completed || [])].sort(
      (a, b) => a.token_number - b.token_number
    );

    if (!items.length) {
      list.innerHTML = '<p class="hint">No patients in today\'s queue yet.</p>';
      return;
    }

    items.forEach((patient) => {
      const row = document.createElement("div");
      row.className = "queue-item";
      row.innerHTML = `
        <div class="queue-token">#${patient.token_number}</div>
        <div>
          <strong>${patient.name}</strong>
          <div class="queue-meta">${formatWait(patient.estimated_wait_minutes)} est. · ${patient.patients_ahead} ahead</div>
        </div>
        <div class="queue-actions">
          <span class="status-pill status-${patient.status}">${statusLabel(patient.status)}</span>
          ${patient.status === "waiting"
            ? `<button data-skip="${patient.id}">Skip</button>`
            : patient.status === "skipped"
              ? `<button data-recall="${patient.id}">Recall</button>`
              : ""}
        </div>
      `;
      list.appendChild(row);
    });

    list.querySelectorAll("[data-skip]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const result = await postJson(`/api/patients/${btn.dataset.skip}/skip/`);
        applyState(result.state);
      });
    });
    list.querySelectorAll("[data-recall]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const result = await postJson(`/api/patients/${btn.dataset.recall}/recall/`);
        applyState(result.state);
      });
    });
  }

  function renderWaitingRoom(state) {
    $("clinic-name").textContent = state.clinic_name;
    $("queue-date").textContent = new Date(state.queue_date).toLocaleDateString(undefined, {
      weekday: "long",
      month: "long",
      day: "numeric",
    });
    $("current-token").textContent = state.current_token ? `#${state.current_token}` : "—";
    $("current-name").textContent = state.current_patient_name || "Please wait";
    $("waiting-count").textContent = state.waiting_count;
    $("estimated-wait").textContent = state.next_tokens.length
      ? formatWait(state.estimated_wait_minutes)
      : "—";
    $("avg-minutes").textContent = state.effective_avg_minutes;

    const chips = $("next-tokens");
    chips.innerHTML = "";
    if (!state.next_tokens.length) {
      chips.innerHTML = '<p class="hint">No one waiting right now.</p>';
    } else {
      state.next_tokens.forEach((token) => {
        const chip = document.createElement("div");
        chip.className = "token-chip";
        chip.textContent = `#${token}`;
        chips.appendChild(chip);
      });
    }

    $("wait-footnote").textContent = state.wait_source === "measured"
      ? `Estimates based on today's actual visit times (avg ${state.measured_avg_minutes} min).`
      : `Estimates based on reception's configured average (${state.avg_consultation_minutes} min).`;
  }

  function renderTrackedPatient(state) {
    const patient = state.tracked_patient;
    if (!patient) {
      $("your-status").textContent = "Token not found for today.";
      return;
    }

    $("your-name").textContent = patient.name;
    $("your-ahead").textContent = patient.patients_ahead;
    $("your-wait").textContent = formatWait(patient.estimated_wait_minutes);

    if (patient.status === "in_consultation") {
      $("your-status").textContent = "It's your turn — please go in now.";
      $("your-status").className = "status-line status-called";
    } else if (patient.status === "completed") {
      $("your-status").textContent = "Your visit is complete. Thank you!";
      $("your-status").className = "status-line";
    } else if (patient.status === "skipped") {
      $("your-status").textContent = "Your token was skipped — please see reception.";
      $("your-status").className = "status-line";
    } else {
      $("your-status").textContent = `${patient.patients_ahead} patient(s) ahead of you.`;
      $("your-status").className = "status-line status-waiting";
    }
  }

  function renderGetToken(state) {
    $("clinic-name").textContent = state.clinic_name;
    $("mini-current").textContent = state.current_token ? `#${state.current_token}` : "—";
    $("mini-waiting").textContent = `${state.waiting_count} waiting`;

    if (myToken) {
      const patient = state.tracked_patient;
      if (patient) {
        $("your-token").textContent = `#${patient.token_number}`;
        renderTrackedPatient(state);
        $("track-link").href = `/track/${patient.token_number}/`;
      }
    }
  }

  function connectStream() {
    const params = myToken ? `?token=${myToken}` : "";
    try {
      source = new EventSource(`/api/stream${params}`);
      source.onmessage = (event) => {
        try {
          applyState(JSON.parse(event.data));
        } catch (err) {
          console.error("Bad queue state", err);
        }
      };
      source.onerror = () => {
        if (source) source.close();
        source = null;
      };
    } catch (err) {
      console.warn("SSE unavailable, using polling only");
    }
  }

  function startPolling() {
    refreshState();
    pollTimer = setInterval(refreshState, 2000);
  }

  function bindReception() {
    $("add-patient-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const name = $("patient-name").value.trim();
      const result = await postJson("/api/patients/", { name });
      applyState(result.state);
      $("patient-name").value = "";
      $("patient-name").focus();

      const box = $("last-added");
      box.classList.remove("hidden");
      box.innerHTML = `<span class="live-dot"></span> Added <strong>${result.patient.name}</strong> as token <strong>#${result.patient.token_number}</strong>`;
    });

    $("call-next-btn").addEventListener("click", async () => {
      const result = await postJson("/api/call-next/");
      applyState(result.state);
    });

    $("save-avg-btn").addEventListener("click", async () => {
      const result = await postJson("/api/settings/", {
        avg_consultation_minutes: Number($("avg-minutes").value),
      });
      applyState(result.state);
    });

    $("reset-day-btn").addEventListener("click", async () => {
      if (confirm("Clear today's entire queue?")) {
        const result = await postJson("/api/reset-day/");
        applyState(result.state);
      }
    });
  }

  function bindGetToken() {
    $("get-token-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const name = $("patient-name").value.trim();
      if (!name) return;

      const result = await postJson("/api/patients/", { name });
      myToken = result.patient.token_number;
      applyState(result.state);
      $("token-form-section").classList.add("hidden");
      $("token-result").classList.remove("hidden");
      $("your-token").textContent = `#${myToken}`;
      $("your-name").textContent = result.patient.name;
      $("track-link").href = `/track/${myToken}/`;

      if (source) source.close();
      connectStream();
    });

    $("new-token-btn").addEventListener("click", () => {
      myToken = null;
      $("patient-name").value = "";
      $("token-form-section").classList.remove("hidden");
      $("token-result").classList.add("hidden");
      $("patient-name").focus();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (page.mode === "reception") bindReception();
    if (page.mode === "get_token") bindGetToken();
    if (page.mode === "track") myToken = page.token;
    connectStream();
    startPolling();
  });
})();
