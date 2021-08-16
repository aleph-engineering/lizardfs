import argparse
import json
import os
import sys
from argparse import Namespace
from typing import Any, Optional

import requests

from tests_list import get_tests_list_with_durations

TESTS_DISPATCHER_URL = os.environ.get("TESTS_DISPATCHER_URL", "http://127.0.0.1:5000/")


def slash_join(*args: str) -> str:
    """Concatenate the arguments avoiding duplicate slash in the joint"""
    return "/".join(arg.strip("/") for arg in args)


def _handle_error_gently(error: requests.exceptions.RequestException) -> None:
    print("Error:", error, file=sys.stderr)


def _handle_error(error: requests.exceptions.RequestException) -> None:
    _handle_error_gently(error)
    sys.exit(1)


def _call(url: str, params: Optional[Any] = None, method: str = "get") -> Any:
    if params is None:
        params = {}
    result = ""
    try:
        if method == "post":
            response = requests.post(url=url, json=params)
        elif method == "put":
            response = requests.put(url=url, json=params)
        elif method == "delete":
            response = requests.delete(url=url, json=params)
        else:
            response = requests.get(url=url, params=params)
        response.raise_for_status()
        result = json.loads(response.content)
    except requests.exceptions.HTTPError as err:
        _handle_error_gently(err)
    except requests.exceptions.ConnectionError as err:
        _handle_error(err)
    except requests.exceptions.Timeout as err:
        _handle_error(err)
    except requests.exceptions.RequestException as err:
        _handle_error(err)
    return result


def push_list(arguments: Namespace) -> Any:
    action_url = slash_join(TESTS_DISPATCHER_URL, "push_list")
    tests = get_tests_list_with_durations(
        arguments.workspace, arguments.test_suite, arguments.excluded_tests
    )
    get_the_second = lambda test_tuple: test_tuple[1]
    sorted_tests = sorted(tests, key=get_the_second, reverse=True)
    test_list = [test_name for (test_name, _) in sorted_tests]
    request_payload = {
        "build_id": arguments.build_id,
        "test_suite": arguments.test_suite,
        "tests": test_list,
    }
    response = _call(url=action_url, params=request_payload, method="post")
    return response


def next_test(arguments: Namespace) -> Any:
    action_url = slash_join(TESTS_DISPATCHER_URL, "next_test")
    request_payload = {
        "build_id": arguments.build_id,
        "test_suite": arguments.test_suite,
    }
    response = _call(url=action_url, params=request_payload, method="get")
    return response["details"]


if __name__ == "__main__":
    """Script which is used to split (all minus manually_excluded) tests from a given test_suite
    into 'nodes_count' groups, so that tests from each group can be run concurrently.
    Goal for the partition is that tests from each group should run for approximately
    the same duration.
    Approximate duration of each test is stored in and fetched from tests/data/'test_suite'.txt"""

    parser = argparse.ArgumentParser(
        description="Filter tests for concurrent runs. All following arguments besides 'excluded_tests' are required."
    )
    parser.add_argument(
        "-a",
        "--action",
        type=str,
        help="The action to request from the dispatcher\n"
        "Currently:\n"
        " - push_list\n"
        " - next_test\n",
    )
    parser.add_argument("-b", "--build_id", type=str, help="Id of the current build")
    parser.add_argument(
        "-w", "--workspace", type=str, help="Path to lizardfs test directory"
    )
    parser.add_argument("-s", "--test_suite", type=str, help="Name of test_suite")
    parser.add_argument(
        "-e",
        "--excluded_tests",
        type=str,
        help="Names of excluded tests, separated by ':'",
    )

    args = parser.parse_args()

    if (
        not args.build_id
        or not args.workspace
        or not args.test_suite
        or not args.action
    ):
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.action == "push_list":
        push_list(args)
    elif args.action == "next_test":
        print(next_test(args))
