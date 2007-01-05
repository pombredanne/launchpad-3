# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugWatch-related browser views."""

__metaclass__ = type
__all__ = [
    'BugWatchSetNavigation',
    'BugWatchEditView']


from zope.component import getUtility

from canonical.launchpad.interfaces import IBugWatch, IBugWatchSet, ILaunchBag
from canonical.launchpad.webapp import (
    action, canonical_url, GetitemNavigation, LaunchpadEditFormView)


class BugWatchSetNavigation(GetitemNavigation):

    usedfor = IBugWatchSet


class BugWatchEditView(LaunchpadEditFormView):
    """View for editing a bug watch."""

    schema = IBugWatch
    field_names = ['bugtracker', 'remotebug']

    @action('Change', name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)

    @property
    def next_url(self):
        return canonical_url(getUtility(ILaunchBag).bugtask)
