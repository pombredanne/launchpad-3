# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SprintAttendance."""

__metaclass__ = type
__all__ = ['SprintAttendanceAddView']

from zope.component import getUtility

from canonical.launchpad.browser.form import FormView

from canonical.launchpad.interfaces import ISprintAttendance, ILaunchBag

from canonical.launchpad.webapp import canonical_url


class SprintAttendanceAddView(FormView):

    schema = ISprintAttendance
    fieldNames = ['time_starts', 'time_ends']
    _arguments = ['time_starts', 'time_ends']

    def process(self, time_starts, time_ends):
        user = getUtility(ILaunchBag).user
        return self.context.attend(user, time_starts, time_ends)

    def nextURL(self):
        return canonical_url(self.context)

