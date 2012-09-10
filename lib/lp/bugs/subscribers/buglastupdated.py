# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Subscriber functions to update IBug.date_last_updated."""

__metaclass__ = type

from datetime import datetime

import pytz
from zope.security.proxy import removeSecurityProxy

from lp.bugs.interfaces.bug import IBug
from lp.bugs.interfaces.hasbug import IHasBug


def update_bug_date_last_updated(object, event):
    """Update IBug.date_last_updated to the current date."""
    # If no fields on the bug have changed, do nothing.
    if event.edited_fields is None:
        return
    if IBug.providedBy(object):
        bug = object
    elif IHasBug.providedBy(object):
        bug = object.bug
    else:
        raise AssertionError(
            "Unable to retrieve current bug to update 'date last updated'. "
            "Event handler expects object implementing IBug or IHasBug. "
            "Got: %s" % repr(object))

    removeSecurityProxy(bug).date_last_updated = datetime.now(pytz.UTC)
