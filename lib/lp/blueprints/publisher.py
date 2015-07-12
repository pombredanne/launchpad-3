# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Blueprints' custom publication."""

__metaclass__ = type
__all__ = [
    'BlueprintsBrowserRequest',
    'BlueprintsLayer',
    'blueprints_request_publication_factory',
    'SpecificationsFacet',
    ]


from zope.interface import implementer
from zope.publisher.interfaces.browser import (
    IBrowserRequest,
    IDefaultBrowserLayer,
    )

from lp.services.webapp.interfaces import IFacet
from lp.services.webapp.publication import LaunchpadBrowserPublication
from lp.services.webapp.servers import (
    LaunchpadBrowserRequest,
    VHostWebServiceRequestPublicationFactory,
    )


@implementer(IFacet)
class SpecificationsFacet:

    name = "specifications"
    rootsite = "blueprints"
    text = "Blueprints"
    default_view = "+specs"


class BlueprintsLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The Blueprints layer."""


@implementer(BlueprintsLayer)
class BlueprintsBrowserRequest(LaunchpadBrowserRequest):
    """Instances of BlueprintsBrowserRequest provide `BlueprintsLayer`."""


def blueprints_request_publication_factory():
    return VHostWebServiceRequestPublicationFactory(
        'blueprints', BlueprintsBrowserRequest, LaunchpadBrowserPublication)
