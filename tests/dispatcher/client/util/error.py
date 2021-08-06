import sys

import requests


def eprint(*args, **kwargs):
    """Print to standard error output"""
    print(*args, file=sys.stderr, **kwargs)


def find_error_reasons(error: requests.exceptions.RequestException) -> [str]:
    """Traverse the exceptions tree gathering the reason message"""
    reasons = []

    if type(error) is str:
        reasons.append(error)

    if hasattr(error, 'reason'):
        more_reasons = find_error_reasons(error.reason)
        if len(more_reasons) > 0:
            reasons.extend(more_reasons)

    if hasattr(error, 'args'):
        for arg in error.args:
            more_reasons = find_error_reasons(arg)
            if len(more_reasons) > 0:
                reasons.extend(more_reasons)

    return reasons
