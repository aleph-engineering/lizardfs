import argparse
import os
import sys
from argparse import Namespace

import requests

from util import slash_join, get_tests_list_with_durations

TESTS_DISPATCHER_URL = os.environ.get("TESTS_DISPATCHER_URL", "http://127.0.0.1:5000/")



def push_list() -> str:
    response = requests.post(url=URL, data=PARAMS)
    print(response.text)
    return response.text


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
        next_test(args)
