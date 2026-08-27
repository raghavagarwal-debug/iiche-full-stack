import urllib.request
import json

# 1. Login
req = urllib.request.Request(
    'https://iiche-full-stack.onrender.com/api/v1/auth/login',
    data=json.dumps({"email": "raghavagarwal.230108@gmail.com", "password": "Admin123"}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
try:
    resp = urllib.request.urlopen(req)
    session_token = resp.headers.get('X-Session-Token')
    print(f"Logged in. Token: {session_token[:10]}...")
except Exception as e:
    print(f"Login failed: {e}")
    exit(1)

# 2. Get all events
req = urllib.request.Request('https://iiche-full-stack.onrender.com/api/v1/events')
resp = urllib.request.urlopen(req)
events = json.loads(resp.read().decode('utf-8'))

# 3. Update all events
for event in events:
    print(f"Updating {event['title']} ({event['id']})...")
    req = urllib.request.Request(
        f"https://iiche-full-stack.onrender.com/api/v1/admin/events/{event['id']}",
        data=json.dumps({"registration_open": False}).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {session_token}',
            'X-Session-Token': session_token
        },
        method='PATCH'
    )
    try:
        urllib.request.urlopen(req)
        print("Success")
    except Exception as e:
        print(f"Failed: {e}")
