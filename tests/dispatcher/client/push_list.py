import os
import sys

import requests

from util import slash_join, get_tests_list_with_durations

TESTS_DISPATCHER_URL = os.environ.get("TESTS_DISPATCHER_URL", "http://127.0.0.1:5000/")
URL = slash_join(TESTS_DISPATCHER_URL, "push_list")

if len(sys.argv) == 3:
    pipeline_id = sys.argv[1]
    tests = sys.argv[2]
else:
    pipeline_id = "1"
    tests = "test01:test02:test03:test04"

PARAMS = {"pipeline_id": pipeline_id, "tests": tests}


def push_list() -> str:
    response = requests.post(url=URL, data=PARAMS)
    print(response.text)
    return response.text


if __name__ == "__main__":
    push_list()
