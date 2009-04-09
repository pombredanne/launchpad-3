# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Browser view class for drivers."""

__metaclass__ = type
__all__ = ["AppointDriverView"]

from zope.interface import providedBy
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import IHasAppointedDriver
from canonical.launchpad.webapp import (
    canonical_url, LaunchpadEditFormView, action)


class AppointDriverView(LaunchpadEditFormView):
    """Browser view for appointing a driver to an object."""

    field_names = ['driver']

    @property
    def schema(self):
        """Return the schema that is the most specific extension of
        IHasAppointedDriver
        """
        assert IHasAppointedDriver.providedBy(self.context), (
            "context should provide IHasAppointedDriver.")
        for interface in providedBy(self.context):
            if interface.isOrExtends(IHasAppointedDriver):
                # XXX matsubara 2007-02-13 bug=84940:
                # removeSecurityProxy() is a workaround.
                return removeSecurityProxy(interface)

    @action('Change', name='change')
    def change_action(self, action, data):
        driver = data['driver']
        self.updateContextFromData(data)
        if driver:
            self.request.response.addNotification(
                "Successfully changed the driver to %s" % driver.displayname)
        else:
            self.request.response.addNotification(
                "Successfully removed the driver")

    @property
    def next_url(self):
        return canonical_url(self.context)
