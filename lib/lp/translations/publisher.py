# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Translations's custom publication."""

__metaclass__ = type
__all__ = [
    'TranslationsBrowserRequest',
    'TranslationsLayer',
    'translations_request_publication_factory',
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
class TranslationsFacet:

    name = "translations"
    rootsite = "translations"
    text = "Translations"
    default_view = "+translations"


class TranslationsLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The Translations layer."""


@implementer(TranslationsLayer)
class TranslationsBrowserRequest(LaunchpadBrowserRequest):
    """Instances of TranslationsBrowserRequest provide `TranslationsLayer`."""

    def __init__(self, body_instream, environ, response=None):
        super(TranslationsBrowserRequest, self).__init__(
            body_instream, environ, response)
        # Many of the responses from Translations vary based on language.
        self.response.setHeader(
            'Vary', 'Cookie, Authorization, Accept-Language')


def translations_request_publication_factory():
    return VHostWebServiceRequestPublicationFactory(
        'translations', TranslationsBrowserRequest,
        LaunchpadBrowserPublication)
