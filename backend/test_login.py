import urllib.request, json
import sys

def test():
    user_data = {'id': 'admin', 'password': '12345'}
    data = json.dumps(user_data).encode('utf8')
    req = urllib.request.Request('http://127.0.0.1:5000/api/login', data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as f:
            print(f"STATUS: {f.getcode()}")
            print(f"BODY: {f.read().decode('utf8')}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test()
