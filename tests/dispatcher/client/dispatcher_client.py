import argparse
import json
import os
import sys
from argparse import Namespace

import requests

from util import eprint, find_error_reasons, slash_join, get_tests_list_with_durations

TESTS_DISPATCHER_URL = os.environ.get("TESTS_DISPATCHER_URL", "http://127.0.0.1:5000/")


def _handle_error_gently(error: requests.exceptions.RequestException):
    eprint("Error:", '\n'.join(find_error_reasons(error)))


def _handle_error(error: requests.exceptions.RequestException):
    _handle_error_gently(error)
    sys.exit(1)


def _call(url: str, params=None, method: str = 'get'):
    if params is None:
        params = {}
    result = None
    try:
        if method == 'post':
            response = requests.post(url=url, json=params)
        elif method == 'put':
            response = requests.put(url=url, json=params)
        elif method == 'delete':
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


def push_list(arguments: Namespace) -> str:
    action_url = slash_join(TESTS_DISPATCHER_URL, "push_list")
    tests = get_tests_list_with_durations(
        arguments.workspace,
        arguments.test_suite,
        arguments.excluded_tests
    )
    sorted_tests = sorted(tests, key=lambda test_tuple: test_tuple[1], reverse=True)
    test_list = [test_name for (test_name, _) in sorted_tests]
    request_payload = {"build_id": arguments.build_id, "test_suite": arguments.test_suite, "tests": test_list}
    response = _call(url=action_url, params=request_payload, method='post')
    return response


def next_test(arguments: Namespace) -> str:
    action_url = slash_join(TESTS_DISPATCHER_URL, "next_test")
    request_payload = {"build_id": arguments.build_id, "test_suite": arguments.test_suite}
    response = _call(url=action_url, params=request_payload, method='get')
    return response['details']


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
        "-a", "--action", type=str, help="The action to request from the dispatcher\n"
                                         "Currently:\n"
                                         " - push_list\n"
                                         " - next_test\n"
    )
    parser.add_argument(
        "-b", "--build_id", type=str, help="Id of the current build"
    )
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

    if args.action == 'push_list':
        push_list(args)
    elif args.action == 'next_test':
        print(next_test(args))
