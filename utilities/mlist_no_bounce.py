# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Disable bounce processing in all existing mailing lists.

This fixes bug 363217 for existing mailing lists.  New lists will
automatically have bounce processing disabled via the new default option

DEFAULT_BOUNCE_PROCESSING = No

Run like so:

    PYTHONPATH=utilities lib/mailman/bin/withlist -l -a -r mlist_no_bounce.fix

You can ignore the final warning you will get that looks something like this:

Unlocking (but not saving) lists: whatever
"""

__metaclass__ = type
__all__ = [
    'fix',
    ]


def fix(mlist):
    mlist.bounce_processing = False
    mlist.Save()
