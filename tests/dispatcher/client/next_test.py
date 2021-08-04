import requests
import sys
import os

TESTS_DISPATCHER_URL = os.environ.get("TESTS_DISPATCHER_URL", "http://127.0.0.1:5000/next_test")

if len(sys.argv) == 2:
    pipeline_id = sys.argv[1]
else:
    pipeline_id = "1"

PARAMS = {"pipeline_id": pipeline_id}

response = requests.get(url=TESTS_DISPATCHER_URL, params=PARAMS)

print(response.text)
