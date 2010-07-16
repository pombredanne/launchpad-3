# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Translations's custom publication."""

__metaclass__ = type
__all__ = [
    'TranslationsBrowserRequest',
    'TranslationsLayer',
    'translations_request_publication_factory',
    ]


from zope.interface import implements
from zope.publisher.interfaces.browser import (
    IBrowserRequest, IDefaultBrowserLayer)

from canonical.launchpad.webapp.publication import LaunchpadBrowserPublication
from canonical.launchpad.webapp.servers import (
    LaunchpadBrowserRequest, VirtualHostRequestPublicationFactory)


class TranslationsLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The Translations layer."""


class TranslationsRequestMixin:

    implements(TranslationsLayer)


class TranslationsBrowserRequest(TranslationsRequestMixin, LaunchpadBrowserRequest):

    def __init__(self, body_instream, environ, response=None):
        super(TranslationsBrowserRequest, self).__init__(
            body_instream, environ, response)
        # Many of the responses from Translations vary based on language.
        self.response.setHeader(
            'Vary', 'Cookie, Authorization, Accept-Language')


def translations_request_publication_factory():
    return VirtualHostRequestPublicationFactory(
        'translations', TranslationsBrowserRequest, LaunchpadBrowserPublication)
