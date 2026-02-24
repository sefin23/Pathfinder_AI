// =====================================================
// tasks.js — Page 2: Task Dashboard for a Life Event
// Pathfinder AI · Layer 1.4
// =====================================================

const API = "http://127.0.0.1:8000";

// Read event ID from URL: tasks.html?id=3
const params  = new URLSearchParams(window.location.search);
const EVENT_ID = parseInt(params.get("id"), 10);

// Cache of all tasks (needed to populate subtask dropdown)
let allTasks = [];

// ── Utilities ─────────────────────────────────────

function showToast(message, type = "success") {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.className = `toast toast--${type} show`;
    setTimeout(() => { toast.className = "toast"; }, 3000);
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function priorityDot(priority) {
    return `<span class="priority-dot priority-dot--${priority}"></span>${priority}`;
}

function formatDate(dateStr) {
    if (!dateStr) return null;
    return new Date(dateStr + "T00:00:00").toLocaleDateString("en-IN", {
        day: "numeric", month: "short", year: "numeric"
    });
}

function isOverdue(dateStr) {
    if (!dateStr) return false;
    return new Date(dateStr + "T00:00:00") < new Date(new Date().toDateString());
}

// ── Load Life Event Details ────────────────────────

async function loadEventDetails() {
    if (!EVENT_ID || isNaN(EVENT_ID)) {
        document.getElementById("event-title-heading").textContent = "Invalid event.";
        return;
    }

    try {
        const res = await fetch(`${API}/life-events/${EVENT_ID}`);
        if (!res.ok) throw new Error("Event not found");
        const ev = await res.json();

        document.title = `Pathfinder AI — ${ev.title}`;
        document.getElementById("nav-event-title").textContent      = ev.title;
        document.getElementById("event-title-heading").textContent   = ev.title;
        document.getElementById("event-desc-text").textContent        = ev.description || "";
    } catch (err) {
        document.getElementById("event-title-heading").textContent = "Event not found.";
        showToast("Could not load event details.", "error");
    }
}

// ── Load & Render Tasks ────────────────────────────

async function loadTasks() {
    try {
        const res = await fetch(`${API}/tasks/?life_event_id=${EVENT_ID}`);
        if (!res.ok) throw new Error("Failed to load tasks");
        allTasks = await res.json();
        renderTasks(allTasks);
        populateParentDropdown(allTasks);
    } catch (err) {
        showToast("Could not load tasks.", "error");
    }
}

function renderTasks(tasks) {
    const list    = document.getElementById("tasks-list");
    const empty   = document.getElementById("tasks-empty");
    const counter = document.getElementById("task-count");

    list.innerHTML = "";

    const total     = tasks.length;
    const completed = tasks.filter(t => t.status === "completed").length;
    counter.textContent = total
        ? `${completed}/${total} completed`
        : "";

    if (total === 0) {
        empty.classList.remove("hidden");
        return;
    }
    empty.classList.add("hidden");

    // Separate top-level tasks and subtasks
    const topLevel = tasks.filter(t => t.parent_id === null || t.parent_id === undefined);
    const subMap   = {};  // parent_id → [subtasks]
    tasks.filter(t => t.parent_id != null).forEach(t => {
        if (!subMap[t.parent_id]) subMap[t.parent_id] = [];
        subMap[t.parent_id].push(t);
    });

    topLevel.forEach(task => {
        list.appendChild(buildTaskItem(task, false));
        // Append any subtasks directly under the parent
        (subMap[task.id] || []).forEach(sub => {
            list.appendChild(buildTaskItem(sub, true));
        });
    });
}

function buildTaskItem(task, isSubtask) {
    const li = document.createElement("li");
    li.className = `task-item${isSubtask ? " task-item--subtask" : ""}`;
    li.id = `task-${task.id}`;

    const isDone    = task.status === "completed";
    const overdue   = !isDone && isOverdue(task.due_date);
    const dueMeta   = task.due_date
        ? `<span style="color:${overdue ? "var(--danger)" : "var(--text-muted)"}">
               ${overdue ? "⚠ Overdue · " : ""}Due: ${formatDate(task.due_date)}
           </span>`
        : "";

    li.innerHTML = `
        <input
            type="checkbox"
            class="task-check"
            id="check-${task.id}"
            aria-label="Mark ${escapeHtml(task.title)} as complete"
            ${isDone ? "checked" : ""}
            onchange="toggleTaskStatus(${task.id}, this.checked)"
        />
        <div class="task-body">
            <div class="task-title ${isDone ? "done" : ""}" id="task-title-${task.id}">
                ${isSubtask ? "↳ " : ""}${escapeHtml(task.title)}
            </div>
            <div class="task-meta">
                ${priorityDot(task.priority)}
                ${dueMeta}
                ${task.description ? `<span>${escapeHtml(task.description)}</span>` : ""}
            </div>
        </div>
        <div class="task-actions">
            <button class="btn btn--ghost btn--sm" onclick="deleteTask(${task.id})" aria-label="Delete task">
                🗑
            </button>
        </div>
    `;

    return li;
}

// ── Populate Parent Dropdown ───────────────────────

function populateParentDropdown(tasks) {
    const select = document.getElementById("task-parent");
    // Reset to just the default option
    select.innerHTML = `<option value="">— Top-level task —</option>`;

    // Only top-level tasks can be parents (no infinite nesting in the UI for now)
    tasks
        .filter(t => t.parent_id === null || t.parent_id === undefined)
        .forEach(t => {
            const opt = document.createElement("option");
            opt.value       = t.id;
            opt.textContent = t.title.length > 50
                ? t.title.slice(0, 50) + "…"
                : t.title;
            select.appendChild(opt);
        });
}

// ── Create Task ────────────────────────────────────

async function createTask() {
    const title    = document.getElementById("task-title").value.trim();
    const desc     = document.getElementById("task-desc").value.trim();
    const priority = document.getElementById("task-priority").value;
    const due      = document.getElementById("task-due").value || null;
    const parentId = document.getElementById("task-parent").value
        ? parseInt(document.getElementById("task-parent").value, 10)
        : null;

    if (!title) {
        showToast("Please enter a task title.", "error");
        document.getElementById("task-title").focus();
        return;
    }

    const btn = document.getElementById("btn-add-task");
    btn.disabled = true;
    btn.textContent = "Adding…";

    try {
        const res = await fetch(`${API}/tasks/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title:         title,
                description:   desc || null,
                priority:      priority,
                due_date:      due,
                life_event_id: EVENT_ID,
                parent_id:     parentId
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to create task");
        }

        // Clear form fields
        document.getElementById("task-title").value    = "";
        document.getElementById("task-desc").value     = "";
        document.getElementById("task-due").value      = "";
        document.getElementById("task-priority").value = "medium";
        document.getElementById("task-parent").value   = "";

        showToast(`Task added!`, "success");
        await loadTasks();

    } catch (err) {
        showToast(err.message, "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "Add Task";
    }
}

// ── Toggle Task Status ─────────────────────────────

async function toggleTaskStatus(taskId, isChecked) {
    const newStatus = isChecked ? "completed" : "pending";

    try {
        const res = await fetch(`${API}/tasks/${taskId}/status`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus })
        });
        if (!res.ok) throw new Error("Status update failed");

        // Update the title style immediately without a full reload
        const titleEl = document.getElementById(`task-title-${taskId}`);
        if (titleEl) {
            isChecked
                ? titleEl.classList.add("done")
                : titleEl.classList.remove("done");
        }

        // Refresh counter
        await loadTasks();

    } catch (err) {
        showToast("Could not update task status.", "error");
        // Revert checkbox
        const checkbox = document.getElementById(`check-${taskId}`);
        if (checkbox) checkbox.checked = !isChecked;
    }
}

// ── Delete Task ────────────────────────────────────

async function deleteTask(taskId) {
    if (!confirm("Delete this task? This will also remove any subtasks.")) return;

    try {
        const res = await fetch(`${API}/tasks/${taskId}`, { method: "DELETE" });
        if (!res.ok && res.status !== 404) throw new Error("Delete failed");

        showToast("Task deleted.", "success");
        await loadTasks();
    } catch (err) {
        showToast("Could not delete task.", "error");
    }
}

// ── Bootstrap ─────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
    if (!EVENT_ID || isNaN(EVENT_ID)) {
        showToast("No life event selected. Redirecting…", "error");
        setTimeout(() => { window.location.href = "index.html"; }, 2000);
        return;
    }
    await loadEventDetails();
    await loadTasks();
});
