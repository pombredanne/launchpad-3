# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Blueprints' custom publication."""

__metaclass__ = type
__all__ = [
    'BlueprintsBrowserRequest',
    'BlueprintsLayer',
    'blueprints_request_publication_factory',
    ]


from zope.interface import implements
from zope.publisher.interfaces.browser import (
    IBrowserRequest, IDefaultBrowserLayer)

from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.servers import (
    LaunchpadBrowserRequest, VirtualHostRequestPublicationFactory)


class BlueprintsLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The Blueprints layer."""


class BlueprintsRequestMixin:

    implements(BlueprintsLayer)


class BlueprintsBrowserRequest(BlueprintsRequestMixin, LaunchpadBrowserRequest):
    pass


def blueprints_request_publication_factory():
    return VirtualHostRequestPublicationFactory(
        'blueprints', BlueprintsBrowserRequest, LaunchpadBrowserPublication)
