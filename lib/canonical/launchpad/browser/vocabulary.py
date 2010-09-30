# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Views which export vocabularies as JSON for widgets."""

__metaclass__ = type

__all__ = [
    'branch_to_vocabularyjson',
    'default_vocabularyjson_adapter',
    'HugeVocabularyJSONView',
    'IPickerEntry',
    'person_to_vocabularyjson',
    'sourcepackagename_to_vocabularyjson',
    ]

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
from lp.app.browser.tales import ObjectImageDisplayAPI
from canonical.launchpad.webapp.vocabulary import IHugeVocabulary
from lp.app.errors import UnexpectedFormData
from lp.code.interfaces.branch import IBranch
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.sourcepackagename import ISourcePackageName
from lp.registry.model.sourcepackagename import getSourcePackageDescriptions

# XXX: EdwinGrubbs 2009-07-27 bug=405476
# This limits the output to one line of text, since the sprite class
# cannot clip the background image effectively for vocabulary items
# with more than single line description below the title.
MAX_DESCRIPTION_LENGTH = 120


class IPickerEntry(Interface):
    """Additional fields that the vocabulary doesn't provide.

    These fields are needed by the Picker Ajax widget."""
    description = Attribute('Description')
    image = Attribute('Image URL')
    css = Attribute('CSS Class')


class PickerEntry:
    """See `IPickerEntry`."""
    implements(IPickerEntry)

    def __init__(self, description=None, image=None, css=None, api_uri=None):
        self.description = description
        self.image = image
        self.css = css


@implementer(IPickerEntry)
@adapter(Interface)
def default_pickerentry_adapter(obj):
    """Adapts Interface to IPickerEntry."""
    extra = PickerEntry()
    if hasattr(obj, 'summary'):
        extra.description = obj.summary
    display_api = ObjectImageDisplayAPI(obj)
    extra.css = display_api.sprite_css()
    if extra.css is None:
        extra.css = 'sprite bullet'
    return extra


@implementer(IPickerEntry)
@adapter(IPerson)
def person_to_pickerentry(person):
    """Adapts IPerson to IPickerEntry."""
    extra = default_pickerentry_adapter(person)
    if person.preferredemail is not None:
        try:
            extra.description = person.preferredemail.email
        except Unauthorized:
            extra.description = '<email address hidden>'
    return extra


@implementer(IPickerEntry)
@adapter(IBranch)
def branch_to_pickerentry(branch):
    """Adapts IBranch to IPickerEntry."""
    extra = default_pickerentry_adapter(branch)
    extra.description = branch.bzr_identity
    return extra


@implementer(IPickerEntry)
@adapter(ISourcePackageName)
def sourcepackagename_to_pickerentry(sourcepackagename):
    """Adapts ISourcePackageName to IPickerEntry."""
    extra = default_pickerentry_adapter(sourcepackagename)
    descriptions = getSourcePackageDescriptions([sourcepackagename])
    extra.description = descriptions.get(
        sourcepackagename.name, "Not yet built")
    return extra


class HugeVocabularyJSONView:
    """Export vocabularies as JSON.

    This was needed by the Picker widget, but could be
    useful for other AJAX widgets.
    """
    DEFAULT_BATCH_SIZE = 10

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        name = self.request.form.get('name')
        if name is None:
            raise MissingInputError('name', '')

        search_text = self.request.form.get('search_text')
        if search_text is None:
            raise MissingInputError('search_text', '')

        try:
            factory = getUtility(IVocabularyFactory, name)
        except ComponentLookupError:
            raise UnexpectedFormData(
                'Unknown vocabulary %r' % name)

        vocabulary = factory(self.context)

        if not IHugeVocabulary.providedBy(vocabulary):
            raise UnexpectedFormData(
                'Non-huge vocabulary %r' % name)

        matches = vocabulary.searchForTerms(search_text)
        batch_navigator = BatchNavigator(matches, self.request)
        total_size = matches.count()

        result = []
        for term in batch_navigator.currentBatch():
            entry = dict(value=term.token, title=term.title)
            # The canonical_url without just the path (no hostname) can
            # be passed directly into the REST PATCH call.
            api_request = IWebServiceClientRequest(self.request)
            try:
                entry['api_uri'] = canonical_url(
                    term.value, request=api_request,
                    path_only_if_possible=True)
            except NoCanonicalUrl:
                # The exception is caught, because the api_url is only
                # needed for inplace editing via a REST call. The
                # form picker doesn't need the api_url.
                entry['api_uri'] = 'Could not find canonical url.'
            picker_entry = IPickerEntry(term.value)
            if picker_entry.description is not None:
                if len(picker_entry.description) > MAX_DESCRIPTION_LENGTH:
                    entry['description'] = (
                        picker_entry.description[:MAX_DESCRIPTION_LENGTH-3]
                        + '...')
                else:
                    entry['description'] = picker_entry.description
            if picker_entry.image is not None:
                entry['image'] = picker_entry.image
            if picker_entry.css is not None:
                entry['css'] = picker_entry.css
            result.append(entry)

        self.request.response.setHeader('Content-type', 'application/json')
        return simplejson.dumps(dict(total_size=total_size, entries=result))
