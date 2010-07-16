# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Bugs's custom publication."""

__metaclass__ = type
__all__ = [
    'BugsBrowserRequest',
    'BugsLayer',
    'bugs_request_publication_factory',
    ]


from zope.interface import implements
from zope.publisher.interfaces.browser import (
    IBrowserRequest, IDefaultBrowserLayer)

from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.servers import (
    LaunchpadBrowserRequest, VirtualHostRequestPublicationFactory)


class BugsLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The Bugs layer."""


class BugsRequestMixin:
    implements(BugsLayer)


class BugsBrowserRequest(BugsRequestMixin, LaunchpadBrowserRequest):
    pass


def bugs_request_publication_factory():
    return VirtualHostRequestPublicationFactory(
        'bugs', BugsBrowserRequest, LaunchpadBrowserPublication)
