# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Subscriber functions to update IBug.date_last_updated."""

__metaclass__ = type

import datetime

import pytz

from canonical.launchpad.interfaces.launchpad import IHasBug
from lp.bugs.interfaces.bug import IBug


def update_bug_date_last_updated(object, event):
    """Update IBug.date_last_updated to the current date."""
    if IBug.providedBy(object):
        current_bug = object
    elif IHasBug.providedBy(object):
        current_bug = object.bug
    else:
        raise AssertionError(
            "Unable to retrieve current bug to update 'date last updated'. "
            "Event handler expects object implementing IBug or IHasBug. "
            "Got: %s" % repr(object))

    UTC = pytz.timezone('UTC')
    now = datetime.datetime.now(UTC)

    current_bug.date_last_updated = now
