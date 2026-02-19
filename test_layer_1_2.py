"""Quick integration test for Layer 1.2 — Life Events & Tasks."""
import requests

BASE = "http://127.0.0.1:8000"

# 1. Create a user
r = requests.post(f"{BASE}/users/", json={"name": "Sefin", "email": "sefin@test.com"})
print("=== Create User ===")
print(f"Status: {r.status_code}")
user = r.json()
print(user)

# 2. Create a life event
r = requests.post(f"{BASE}/life-events/", json={
    "title": "Moving to Bangalore for first job",
    "description": "Starting as a software engineer. Need to set up everything.",
    "user_id": user["id"]
})
print("\n=== Create Life Event ===")
print(f"Status: {r.status_code}")
event = r.json()
print(event)

# 3. Create tasks under that life event
tasks_data = [
    {"title": "Find PG accommodation", "priority": "high", "life_event_id": event["id"]},
    {"title": "Open salary bank account", "priority": "high", "life_event_id": event["id"]},
    {"title": "Set up UPI payments", "priority": "medium", "life_event_id": event["id"]},
    {"title": "Register at local police station", "priority": "low", "life_event_id": event["id"]},
]
print("\n=== Create Tasks ===")
for t in tasks_data:
    r = requests.post(f"{BASE}/tasks/", json=t)
    task_json = r.json()
    print(f"  {r.status_code} - {task_json['title']} ({task_json['status']})")

# 4. Update task 1 status to in_progress
r = requests.patch(f"{BASE}/tasks/1/status", json={"status": "in_progress"})
print("\n=== Update Task 1 to in_progress ===")
task_json = r.json()
print(f"Status: {r.status_code} - {task_json['title']}: {task_json['status']}")

# 5. Get life event with all tasks
r = requests.get(f"{BASE}/life-events/{event['id']}")
print("\n=== Get Life Event with Tasks ===")
print(f"Status: {r.status_code}")
data = r.json()
print(f"Event: {data['title']} ({data['status']})")
print("Tasks:")
for task in data["tasks"]:
    print(f"  - {task['title']} [{task['status']}] (priority: {task['priority']})")

# 6. Filter tasks by life event
r = requests.get(f"{BASE}/tasks/", params={"life_event_id": event["id"]})
print(f"\n=== Filter Tasks by Life Event ===")
print(f"Status: {r.status_code}, Count: {len(r.json())}")

# 7. Filter life events by user
r = requests.get(f"{BASE}/life-events/", params={"user_id": user["id"]})
print(f"\n=== Filter Life Events by User ===")
print(f"Status: {r.status_code}, Count: {len(r.json())}")

print("\n✅ ALL TESTS PASSED")
