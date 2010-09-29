# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementations of the XML-RPC APIs for codehosting."""

__metaclass__ = type
__all__ = [
    'LinkCheckerAPI',
    ]

from zope.interface import (
    implements,
    Interface,
    )

from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.interfaces import ILaunchpadApplication

class ILinkCheckerApplication(ILaunchpadApplication):
    """Link Checker application root."""

class ILinkCheckerAPI(Interface):
    def check_links(self, links):
        """ Do some checking."""

class LinkCheckerAPI(LaunchpadView):
    """See `LinkCheckerAPI`."""

    implements(ILinkCheckerAPI)

    def check_links(self, links):
        if links is None:
            links = ['a', 'b', 'c']
        return ','.join(links)

