# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""General useful stuff."""

__metaclass__ = type
__all__ = [
    'find_datetime_string',
    'make_datetime_string',
    ]


import re

from datetime import datetime


def make_datetime_string(when=None):
    """Generate a simple formatted date and time string.

    This is intended to be embedded in text to be later found by
    `find_datetime_string`.
    """
    if when is None:
        when = datetime.utcnow()
    return when.strftime('%Y-%m-%d-%H%M')


re_find_datetime = re.compile(
    r'(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})')

def find_datetime_string(text):
    """Search for a simple date and time in arbitrary text.

    The format searched for is %Y-%m-%d-%H%M - the same as produced by
    `make_datetime_string`.
    """
    match = re_find_datetime.search(text)
    if match is None:
        return None
    else:
        return datetime(*(int(part) for part in match.groups()))
