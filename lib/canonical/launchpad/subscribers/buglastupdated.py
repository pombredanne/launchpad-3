# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Subscriber functions to update IBug.date_last_updated."""

__metaclass__ = type

import datetime
import pytz
from zope.component import getUtility
from canonical.launchpad.interfaces import ILaunchBag

def update_bug_date_last_updated(object, event):
    """Update IBug.date_last_updated to the current date."""
    current_bug = getUtility(ILaunchBag).bug

    UTC = pytz.timezone('UTC')
    now = datetime.datetime.now(UTC)

    current_bug.date_last_updated = now
