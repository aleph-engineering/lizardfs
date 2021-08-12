import os
from typing import List, Set, Tuple


def get_excluded_tests_two_types(
    excluded_tests: List[str], test_suite: str
) -> Set[str]:
    """Returns a list with excluded tests. Each test is there twice, e.g. both
    'LongSystemTests.testname' and 'testname'."""

    excl_tests_two_types = set()  # both test_suite.testname and just testname
    for t in excluded_tests:
        excl_tests_two_types.add(t)
        if "." in t:
            excl_tests_two_types.add(t.split(".")[1])
        else:
            excl_tests_two_types.add(test_suite + "." + t)
    return excl_tests_two_types


def get_gtest_testlist(
    workspace: str, test_suite: str, excluded_tests: List[str]
) -> List[str]:
    """Returns a list of (all minus excluded) tests in a given test_suite"""

    tests_list = os.popen(
        workspace + "/install/lizardfs/bin/lizardfs-tests "
        "--gtest_list_tests --gtest_filter=" + test_suite + "*"
    )

    # Remove unnecessary lines - go just to tests' list
    tests_list.readline()
    tests_list.readline()

    excl_tests_two_types = get_excluded_tests_two_types(excluded_tests, test_suite)
    return [t.strip() for t in tests_list if t.strip() not in excl_tests_two_types]


def get_data_testlist(
    workspace: str, test_suite: str, excluded_tests: List[str]
) -> List[Tuple[str, float]]:
    """Returns a list of (all minus excluded) tests in a given test_suite,
    The list is of tuples (test_name, test_duration).
    Data is fetched from tests/data/'test_suite'.txt file"""

    excl_tests_two_types = get_excluded_tests_two_types(excluded_tests, test_suite)

    tests_data = []
    with open(workspace + "/tests/data/" + test_suite + ".txt", "r") as tests_list_data:
        for data_line in tests_list_data:
            div = data_line.split("=")
            if div[0] not in excl_tests_two_types:
                tests_data.append((div[0], float(div[1])))
    return tests_data


def get_tests_list_with_durations(
    workspace: str, test_suite: str, excluded_tests: List[str]
) -> List[Tuple[str, float]]:
    """Returns list with tuples (testname, duration of test)"""

    gtest_testlist = get_gtest_testlist(workspace, test_suite, excluded_tests)
    data_testlist = get_data_testlist(workspace, test_suite, excluded_tests)

    gtest_tests_set = set(gtest_testlist)
    data_tests_set = {t[0] for t in data_testlist}
    lacking_tests = gtest_tests_set - data_tests_set
    if len(lacking_tests) > 0:
        raise Exception(
            "Incomplete data/'test_suite'.txt file.\nDoesn't contain following tests: "
            + str(lacking_tests)
        )

    return data_testlist
