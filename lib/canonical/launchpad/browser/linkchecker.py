# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Link checker interfaces."""

__metaclass__ = type

__all__ = [
    'LinkCheckerAPI',
    'LinkCheckerURL',
    ]

from canonical.launchpad.interfaces.linkchecker import ILinkCheckerAPI
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData

from lazr.restful.interfaces import IWebServiceClientRequest
import simplejson
from zope.app.form.interfaces import MissingInputError
from zope.app.schema.vocabulary import IVocabularyFactory
from zope.component import (
    adapter,
    getUtility,
    )
from zope.component.interfaces import ComponentLookupError
from zope.interface import (
    Attribute,
    implementer,
    implements,
    Interface,
    )
from zope.security.interfaces import Unauthorized

from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.interfaces import NoCanonicalUrl
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.tales import ObjectImageDisplayAPI
from canonical.launchpad.webapp.vocabulary import IHugeVocabulary
from lp.app.errors import UnexpectedFormData
from lp.code.interfaces.branch import IBranch
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.sourcepackagename import ISourcePackageName
from lp.registry.model.sourcepackagename import getSourcePackageDescriptions

class LinkCheckerAPI:
    """See `ILinkCheckerAPI`."""

    implements(ILinkCheckerAPI)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def check_links(self, links):
        if links is None:
            links = ['a', 'b', 'c']
        return ','.join(links)

    def __call__(self):

        result = []
    #    for term in batch_navigator.currentBatch():
    #        entry = dict(value=term.token, title=term.title)
    #        # The canonical_url without just the path (no hostname) can
    #        # be passed directly into the REST PATCH call.
    #        api_request = IWebServiceClientRequest(self.request)
    #        try:
    #            entry['api_uri'] = canonical_url(
    #                term.value, request=api_request,
    #                path_only_if_possible=True)
    #        except NoCanonicalUrl:
    #            # The exception is caught, because the api_url is only
    #            # needed for inplace editing via a REST call. The
    #            # form picker doesn't need the api_url.
    #            entry['api_uri'] = 'Could not find canonical url.'
    #        picker_entry = IPickerEntry(term.value)
    #        if picker_entry.description is not None:
    #            if len(picker_entry.description) > MAX_DESCRIPTION_LENGTH:
    #                entry['description'] = (
    #                    picker_entry.description[:MAX_DESCRIPTION_LENGTH-3]
    #                    + '...')
    #            else:
    #                entry['description'] = picker_entry.description
    #        if picker_entry.image is not None:
    #            entry['image'] = picker_entry.image
    #        if picker_entry.css is not None:
    #            entry['css'] = picker_entry.css
    #        result.append(entry)

        result.append({'test': '123'})
        self.request.response.setHeader('Content-type', 'application/json')
        return simplejson.dumps(dict(total_size=4, entries=result))


class LinkCheckerURL:
    """URL creation rules."""
    implements(ICanonicalUrlData)

    inside = None
    rootsite = None

    def __init__(self, context):
        self.context = context

    @property
    def path(self):
        """Return the path component of the URL."""
        return u'check_links'
