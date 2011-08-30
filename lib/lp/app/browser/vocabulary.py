# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Views which export vocabularies as JSON for widgets."""

__metaclass__ = type

__all__ = [
    'HugeVocabularyJSONView',
    'IPickerEntrySource',
    'get_person_picker_entry_metadata',
    ]

from itertools import izip

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
    implements,
    Interface,
    )
from zope.security.interfaces import Unauthorized

from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.interfaces import NoCanonicalUrl
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.vocabulary import IHugeVocabulary
from lp.app.browser.tales import (
    DateTimeFormatterAPI,
    IRCNicknameFormatterAPI,
    ObjectImageDisplayAPI,
    )
from lp.app.errors import UnexpectedFormData
from lp.code.interfaces.branch import IBranch
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.sourcepackagename import ISourcePackageName
from lp.registry.model.pillaraffiliation import IHasAffiliation
from lp.registry.model.sourcepackagename import getSourcePackageDescriptions
from lp.services.features import getFeatureFlag
from lp.soyuz.interfaces.archive import IArchive

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
    alt_title = Attribute('Alternative title')
    title_link = Attribute('URL used for anchor on title')
    details = Attribute('An optional list of information about the entry')
    alt_title_link = Attribute('URL used for anchor on alt title')
    link_css = Attribute('CSS Class for links')
    badges = Attribute('List of badge img attributes')
    metadata = Attribute('Metadata about the entry')


class PickerEntry:
    """See `IPickerEntry`."""
    implements(IPickerEntry)

    def __init__(self, description=None, image=None, css=None, alt_title=None,
                 title_link=None, details=None, alt_title_link=None,
                 link_css='sprite new-window', badges=None, metadata=None):
        self.description = description
        self.image = image
        self.css = css
        self.alt_title = alt_title
        self.title_link = title_link
        self.details = details
        self.alt_title_link = alt_title_link
        self.link_css = link_css
        self.badges = badges
        self.metadata = metadata


class IPickerEntrySource(Interface):
    """An adapter used to convert vocab terms to picker entries."""

    def getPickerEntries(term_values, context_object, **kwarg):
        """Return picker entries for the specified term values.

        :param term_values: a collection of vocab term values
        :param context_object: the current context used to determine any
            affiliation for the resulting picker entries. eg a picker used to
            select a bug task assignee will have context_object set to the bug
            task.
        """


@adapter(Interface)
class DefaultPickerEntrySourceAdapter(object):
    """Adapts Interface to IPickerEntrySource."""

    implements(IPickerEntrySource)

    def __init__(self, context):
        self.context = context

    def getPickerEntries(self, term_values, context_object, **kwarg):
        """See `IPickerEntrySource`"""
        entries = []
        for term_value in term_values:
            extra = PickerEntry()
            if hasattr(term_value, 'summary'):
                extra.description = term_value.summary
            display_api = ObjectImageDisplayAPI(term_value)
            extra.css = display_api.sprite_css()
            if extra.css is None:
                extra.css = 'sprite bullet'
            entries.append(extra)
        return entries


def get_person_picker_entry_metadata(picker_entry):
    """Return the picker entry meta for a given result value."""
    if picker_entry is not None and IPerson.providedBy(picker_entry):
        return "team" if picker_entry.is_team else "person"
    return None


@adapter(IPerson)
class PersonPickerEntrySourceAdapter(DefaultPickerEntrySourceAdapter):
    """Adapts IPerson to IPickerEntrySource."""

    def getPickerEntries(self, term_values, context_object, **kwarg):
        """See `IPickerEntrySource`"""
        picker_entries = (
            super(PersonPickerEntrySourceAdapter, self)
                .getPickerEntries(term_values, context_object))

        personpicker_affiliation_enabled = kwarg.get(
                                    'personpicker_affiliation_enabled', False)
        affiliated_context = IHasAffiliation(context_object, None)
        if (affiliated_context is not None
            and personpicker_affiliation_enabled):
            # If a person is affiliated with the associated_object then we
            # can display a badge.
            badges = affiliated_context.getAffiliationBadges(term_values)
            for picker_entry, badges in izip(picker_entries, badges):
                picker_entry.badges = []
                for badge_info in badges:
                    picker_entry.badges.append(
                        dict(url=badge_info.url, alt=badge_info.alt_text))

        picker_expander_enabled = kwarg.get('picker_expander_enabled', False)
        for person, picker_entry in izip(term_values, picker_entries):
            if picker_expander_enabled:
                picker_entry.details = []

            if person.preferredemail is not None:
                if person.hide_email_addresses:
                    picker_entry.description = '<email address hidden>'
                else:
                    try:
                        picker_entry.description = person.preferredemail.email
                    except Unauthorized:
                        picker_entry.description = '<email address hidden>'

            picker_entry.metadata = get_person_picker_entry_metadata(person)
            enhanced_picker_enabled = kwarg.get(
                                            'enhanced_picker_enabled', False)
            if enhanced_picker_enabled:
                # We will display the person's name (launchpad id) after their
                # displayname.
                picker_entry.alt_title = person.name
                # We will linkify the person's name so it can be clicked to
                # open the page for that person.
                picker_entry.alt_title_link = canonical_url(
                                                person, rootsite='mainsite')
                # We will display the person's irc nick(s) after their email
                # address in the description text.
                irc_nicks = None
                if person.ircnicknames:
                    irc_nicks = ", ".join(
                        [IRCNicknameFormatterAPI(ircid).displayname()
                        for ircid in person.ircnicknames])
                if irc_nicks and not picker_expander_enabled:
                    if picker_entry.description:
                        picker_entry.description = ("%s (%s)" %
                            (picker_entry.description, irc_nicks))
                    else:
                        picker_entry.description = "%s" % irc_nicks
                if picker_expander_enabled:
                    if irc_nicks:
                        picker_entry.details.append(irc_nicks)
                    if person.is_team:
                        picker_entry.details.append(
                            'Team members: %s' % person.all_member_count)
                    else:
                        picker_entry.details.append(
                            'Member since %s' % DateTimeFormatterAPI(
                                person.datecreated).date())
        return picker_entries


@adapter(IBranch)
class BranchPickerEntrySourceAdapter(DefaultPickerEntrySourceAdapter):
    """Adapts IBranch to IPickerEntrySource."""

    def getPickerEntries(self, term_values, context_object, **kwarg):
        """See `IPickerEntrySource`"""
        entries = (
            super(BranchPickerEntrySourceAdapter, self)
                    .getPickerEntries(term_values, context_object, **kwarg))
        for branch, picker_entry in izip(term_values, entries):
            picker_entry.description = branch.bzr_identity
        return entries


class TargetPickerEntrySourceAdapter(DefaultPickerEntrySourceAdapter):
    """Adapt targets (Product, Package, Distribution) to PickerEntrySource."""

    def getDescription(self, target):
        """Gets the description data for target picker entries."""
        raise NotImplemented

    def getPickerEntries(self, term_values, context_object, **kwarg):
        """See `IPickerEntrySource`"""
        entries = (
            super(TargetPickerEntrySourceAdapter, self)
                .getPickerEntries(term_values, context_object, **kwarg))
        for target, picker_entry in izip(term_values, entries):
            picker_entry.description = self.getDescription(target)
        return entries


@adapter(ISourcePackageName)
class SourcePackageNamePickerEntrySourceAdapter(
                                            DefaultPickerEntrySourceAdapter):
    """Adapts ISourcePackageName to IPickerEntrySource."""

    def getPickerEntries(self, term_values, context_object, **kwarg):
        """See `IPickerEntrySource`"""
        entries = (
            super(SourcePackageNamePickerEntrySourceAdapter, self)
                .getPickerEntries(term_values, context_object, **kwarg))
        for sourcepackagename, picker_entry in izip(term_values, entries):
            descriptions = getSourcePackageDescriptions([sourcepackagename])
            picker_entry.description = descriptions.get(
                sourcepackagename.name, "Not yet built")
        return entries


@adapter(IDistributionSourcePackage)
class DistributionSourcePackagePickerEntrySourceAdapter(
    TargetPickerEntrySourceAdapter):
    """Adapts IDistributionSourcePackage to IPickerEntrySource."""

    def getDescription(self, target):
        """See `TargetPickerEntrySource`"""
        binaries = target.publishing_history[0].getBuiltBinaries()
        binary_names = [binary.binary_package_name for binary in binaries]
        if binary_names != []:
            description = ', '.join(binary_names)
        else:
            description = 'Not yet built.'
        return description


@adapter(IProduct)
class ProductPickerEntrySourceAdapter(TargetPickerEntrySourceAdapter):
    """Adapts IProduct to IPickerEntrySource."""

    def getDescription(self, target):
        """See `TargetPickerEntrySource`"""
        return target.summary


@adapter(IDistribution)
class DistributionPickerEntrySourceAdapter(TargetPickerEntrySourceAdapter):

    def getDescription(self, target):
        """See `TargetPickerEntrySource`"""
        return target.summary


@adapter(IArchive)
class ArchivePickerEntrySourceAdapter(DefaultPickerEntrySourceAdapter):
    """Adapts IArchive to IPickerEntrySource."""

    def getPickerEntries(self, term_values, context_object, **kwarg):
        """See `IPickerEntrySource`"""
        entries = (
            super(ArchivePickerEntrySourceAdapter, self)
                    .getPickerEntries(term_values, context_object, **kwarg))
        for archive, picker_entry in izip(term_values, entries):
            picker_entry.description = '%s/%s' % (
                                       archive.owner.name, archive.name)
        return entries


class HugeVocabularyJSONView:
    """Export vocabularies as JSON.

    This was needed by the Picker widget, but could be
    useful for other AJAX widgets.
    """
    DEFAULT_BATCH_SIZE = 10

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.enhanced_picker_enabled = bool(
            getFeatureFlag('disclosure.picker_enhancements.enabled'))
        self.picker_expander_enabled = bool(
            getFeatureFlag('disclosure.picker_expander.enabled'))
        self.personpicker_affiliation_enabled = bool(
            getFeatureFlag('disclosure.personpicker_affiliation.enabled'))

    def __call__(self):
        name = self.request.form.get('name')
        if name is None:
            raise MissingInputError('name', '')

        search_text = self.request.form.get('search_text')
        if search_text is None:
            raise MissingInputError('search_text', '')
        search_filter = self.request.form.get('search_filter')

        try:
            factory = getUtility(IVocabularyFactory, name)
        except ComponentLookupError:
            raise UnexpectedFormData(
                'Unknown vocabulary %r' % name)

        vocabulary = factory(self.context)

        if IHugeVocabulary.providedBy(vocabulary):
            matches = vocabulary.searchForTerms(search_text, search_filter)
            total_size = matches.count()
        else:
            matches = list(vocabulary)
            total_size = len(matches)

        batch_navigator = BatchNavigator(matches, self.request)

        # We need to collate what IPickerEntrySource adapters are required for
        # the items in the current batch. We expect that the batch will be
        # homogenous and so only one adapter instance is required, but we
        # allow for the case where the batch may contain disparate entries
        # requiring different adapter implementations.

        # A mapping from adapter class name -> adapter instance
        adapter_cache = {}
        # A mapping from adapter class name -> list of vocab terms
        picker_entry_terms = {}
        for term in batch_navigator.currentBatch():
            picker_entry_source = IPickerEntrySource(term.value)
            adapter_class = picker_entry_source.__class__.__name__
            picker_terms = picker_entry_terms.get(adapter_class)
            if picker_terms is None:
                picker_terms = []
                picker_entry_terms[adapter_class] = picker_terms
                adapter_cache[adapter_class] = picker_entry_source
            picker_terms.append(term.value)

        # A mapping from vocab terms -> picker entries
        picker_term_entries = {}

        # For the list of terms associated with a picker adapter, we get the
        # corresponding picker entries by calling the adapter.
        for adapter_class, term_values in picker_entry_terms.items():
            picker_entries = adapter_cache[adapter_class].getPickerEntries(
                term_values,
                self.context,
                enhanced_picker_enabled=self.enhanced_picker_enabled,
                picker_expander_enabled=self.picker_expander_enabled,
                personpicker_affiliation_enabled=(
                    self.personpicker_affiliation_enabled))
            for term_value, picker_entry in izip(term_values, picker_entries):
                picker_term_entries[term_value] = picker_entry

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
            picker_entry = picker_term_entries[term.value]
            if picker_entry.description is not None:
                if len(picker_entry.description) > MAX_DESCRIPTION_LENGTH:
                    entry['description'] = (
                        picker_entry.description[:MAX_DESCRIPTION_LENGTH - 3]
                        + '...')
                else:
                    entry['description'] = picker_entry.description
            if picker_entry.image is not None:
                entry['image'] = picker_entry.image
            if picker_entry.css is not None:
                entry['css'] = picker_entry.css
            if picker_entry.alt_title is not None:
                entry['alt_title'] = picker_entry.alt_title
            if picker_entry.title_link is not None:
                entry['title_link'] = picker_entry.title_link
            if picker_entry.details is not None:
                entry['details'] = picker_entry.details
            if picker_entry.alt_title_link is not None:
                entry['alt_title_link'] = picker_entry.alt_title_link
            if picker_entry.link_css is not None:
                entry['link_css'] = picker_entry.link_css
            if picker_entry.badges:
                entry['badges'] = picker_entry.badges
            if picker_entry.metadata is not None:
                entry['metadata'] = picker_entry.metadata
            result.append(entry)

        self.request.response.setHeader('Content-type', 'application/json')
        return simplejson.dumps(dict(total_size=total_size, entries=result))
