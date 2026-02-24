// =====================================================
// events.js — Page 1: Life Events List
// Pathfinder AI · Layer 1.4
// =====================================================

const API = "http://127.0.0.1:8000";

// ── Utilities ─────────────────────────────────────

function showToast(message, type = "success") {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.className = `toast toast--${type} show`;
    setTimeout(() => { toast.className = "toast"; }, 3000);
}

function statusBadge(status) {
    return `<span class="badge badge--${status}">${status}</span>`;
}

function formatDate(isoString) {
    if (!isoString) return "";
    return new Date(isoString).toLocaleDateString("en-IN", {
        day: "numeric", month: "short", year: "numeric"
    });
}

// ── Load & Render Life Events ──────────────────────

async function loadEvents() {
    try {
        // user_id=1 is hardcoded — no auth in Layer 1.4
        const res = await fetch(`${API}/life-events/?user_id=1`);
        if (!res.ok) throw new Error("Failed to load events");
        const events = await res.json();
        renderEvents(events);
    } catch (err) {
        showToast("Could not connect to backend. Is the server running?", "error");
    }
}

function renderEvents(events) {
    const list    = document.getElementById("events-list");
    const empty   = document.getElementById("events-empty");
    const counter = document.getElementById("event-count");

    counter.textContent = events.length
        ? `${events.length} event${events.length > 1 ? "s" : ""}`
        : "";

    if (events.length === 0) {
        empty.classList.remove("hidden");
        return;
    }

    empty.classList.add("hidden");

    // Clear existing cards (re-render on refresh)
    list.innerHTML = "";

    events.forEach(ev => {
        const card = document.createElement("div");
        card.className = "card";
        card.setAttribute("role", "button");
        card.setAttribute("tabindex", "0");
        card.setAttribute("aria-label", `Open life event: ${ev.title}`);
        card.id = `event-card-${ev.id}`;

        card.innerHTML = `
            <div class="flex-between">
                <span class="card-title">${escapeHtml(ev.title)}</span>
                ${statusBadge(ev.status)}
            </div>
            <div class="card-meta mt-8">
                ${ev.description ? escapeHtml(ev.description) + " · " : ""}
                Created ${formatDate(ev.created_at)}
            </div>
        `;

        // Click or Enter → go to tasks page
        const go = () => {
            window.location.href = `tasks.html?id=${ev.id}`;
        };
        card.addEventListener("click", go);
        card.addEventListener("keydown", e => { if (e.key === "Enter") go(); });

        list.appendChild(card);
    });
}

// ── Create Life Event ──────────────────────────────

async function createLifeEvent() {
    const title  = document.getElementById("event-title").value.trim();
    const desc   = document.getElementById("event-desc").value.trim();
    const userId = parseInt(document.getElementById("event-user-id").value, 10);

    if (!title) {
        showToast("Please enter an event title.", "error");
        document.getElementById("event-title").focus();
        return;
    }

    const btn = document.getElementById("btn-create-event");
    btn.disabled = true;
    btn.textContent = "Creating…";

    try {
        const res = await fetch(`${API}/life-events/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title:   title,
                description: desc || null,
                user_id: userId
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Creation failed");
        }

        // Clear form
        document.getElementById("event-title").value = "";
        document.getElementById("event-desc").value  = "";

        showToast(`"${title}" created!`, "success");
        await loadEvents(); // Refresh list

    } catch (err) {
        showToast(err.message, "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "Create Event";
    }
}

// ── Security: Prevent XSS ─────────────────────────

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// ── Bootstrap ─────────────────────────────────────

// First, ensure user_id=1 exists in the backend (creates it if missing)
async function ensureDefaultUser() {
    try {
        // Try to list events for user 1 to see if the call works.
        // If user doesn't exist backend will return empty list (not an error).
        await fetch(`${API}/life-events/?user_id=1`);
    } catch (_) {
        // Server might be down — loadEvents() will surface the error
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    await ensureDefaultUser();
    await loadEvents();
});
