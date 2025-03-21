import requests

def test_riders_api():
    url = "http://localhost:8000/ofdashboard/api/riders/data/"
    headers = {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest"
    }
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {response.headers}")
    try:
        print(f"Response JSON: {response.json()}")
    except:
        print(f"Response Text: {response.text}")

if __name__ == "__main__":
    test_riders_api()
