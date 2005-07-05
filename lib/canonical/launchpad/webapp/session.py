# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Support for browser-cookie sessions."""

__metaclass__ = type

from zope.app.session.session import PersistentSessionDataContainer
from zope.app.session.http import CookieClientIdManager

from canonical.launchpad.webapp.zodb import zodbconnection


class LaunchpadCookieClientIdManager(CookieClientIdManager):

    def __init__(self):
        CookieClientIdManager.__init__(self)
        self.namespace = "launchpad"
        self.cookieLifetime = 24 * 60 * 60
        
class LaunchpadSessionDataContainer(PersistentSessionDataContainer):

    def __init__(self):
        # The timeout is in seconds
        self.timeout = 6 * 60 * 60
        self.resolution = 50*60

    def _getData(self):
        return zodbconnection.sessiondata

    data = property(_getData, None)

idmanager = LaunchpadCookieClientIdManager()
datacontainer = LaunchpadSessionDataContainer()
