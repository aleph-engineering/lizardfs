import os
import sys

import requests

from util import slash_join

TESTS_DISPATCHER_URL = os.environ.get("TESTS_DISPATCHER_URL", "http://127.0.0.1:5000/")
URL = slash_join(TESTS_DISPATCHER_URL, "next_test")

if len(sys.argv) == 2:
    pipeline_id = sys.argv[1]
else:
    pipeline_id = "1"

PARAMS = {"pipeline_id": pipeline_id}

response = requests.get(url=URL, params=PARAMS)

print(response.text)
