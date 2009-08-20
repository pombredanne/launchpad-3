# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Person-related translations view classes."""

__metaclass__ = type

__all__ = [
    'PersonTranslationView',
    'PersonTranslationRelicensingView',
]

from datetime import datetime, timedelta
import pytz
import urllib
from zope.app.form.browser import TextWidget
from zope.component import getUtility

from canonical.launchpad import _
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.cachedproperty import cachedproperty
from canonical.launchpad.webapp import (
    LaunchpadFormView, Link, action, canonical_url, custom_widget)
from canonical.launchpad.webapp.menu import NavigationMenu
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.widgets import LaunchpadRadioWidget
from lp.registry.interfaces.person import IPerson
from lp.translations.interfaces.pofiletranslator import (
    IPOFileTranslatorSet)
from lp.translations.interfaces.translationrelicensingagreement import (
    ITranslationRelicensingAgreementEdit,
    TranslationRelicensingAgreementOptions)
from lp.translations.interfaces.translationsperson import (
    ITranslationsPerson)
from lp.translations.model.pofile import POFile
from lp.translations.model.productserieslanguage import ProductSeriesLanguage


def count_unreviewed(pofile):
    """Return number of strings in `pofile` that need review."""
    return pofile.unreviewedCount()


def count_untranslated(pofile):
    """Return number of untranslated strings in `pofile`."""
    return pofile.untranslatedCount()


class PersonTranslationsMenu(NavigationMenu):

    usedfor = IPerson
    facet = 'translations'
    links = ('overview', 'licensing', 'imports')

    def overview(self):
        text = 'Overview'
        return Link('', text)

    def imports(self):
        text = 'Import queue'
        return Link('+imports', text)

    def licensing(self):
        text = 'Translations licensing'
        enabled = (self.context == self.user)
        return Link('+licensing', text, enabled=enabled)


class PersonTranslationView(LaunchpadView):
    """View for translation-related Person pages."""

    _pofiletranslator_cache = None

    history_horizon = None

    @cachedproperty
    def batchnav(self):
        translations_person = ITranslationsPerson(self.context)
        batchnav = BatchNavigator(
            translations_person.translation_history, self.request)

        pofiletranslatorset = getUtility(IPOFileTranslatorSet)
        batch = batchnav.currentBatch()
        self._pofiletranslator_cache = (
            pofiletranslatorset.prefetchPOFileTranslatorRelations(batch))

        return batchnav

    @cachedproperty
    def translation_groups(self):
        """Return translation groups a person is a member of."""
        translations_person = ITranslationsPerson(self.context)
        return list(translations_person.translation_groups)

    @cachedproperty
    def translators(self):
        """Return translators a person is a member of."""
        translations_person = ITranslationsPerson(self.context)
        return list(translations_person.translators)

    @cachedproperty
    def person_filter_querystring(self):
        """Return person's name appropriate for including in links."""
        return urllib.urlencode({'person': self.context.name})

    @property
    def person_is_reviewer(self):
        """Is this person in a translation group?"""
        return len(self.translation_groups) != 0

    @property
    def person_is_translator(self):
        """Is this person active in translations?"""
        return self.context.hasKarma('translations')

    def should_display_message(self, translationmessage):
        """Should a certain `TranslationMessage` be displayed.

        Return False if user is not logged in and message may contain
        sensitive data such as email addresses.

        Otherwise, return True.
        """
        if self.user:
            return True
        return not (
            translationmessage.potmsgset.hide_translations_from_anonymous)

    _pofile_review_suffix = '/+translate?show=new_suggestions'

    _pofile_translate_suffix = '/+translate?show=untranslated'

    def _composePOFileLinks(self, pofiles, suffix):
        """Compose URLs for given `POFile`s.

        :param pofiles: Sequence of `POFile`s.
        :param suffix: String to append to each `POFile`s URL.
        """
        return [canonical_url(pofile) + suffix for pofile in pofiles]

    def _findBestCommonLinks(self, pofiles, pofile_suffix):
        """Find best links to a bunch of related `POFile`s.

        The `POFile`s must either be in the same `Product`, or in the
        same `DistroSeries` and `SourcePackageName`.
        
        This method finds the greatest common denominators between them,
        and returns a list of links to them: the individual translation
        if there is only one, the template if multiple translations of
        one template are involved, and so on.

        :param pofiles: List of `POFile`s.
        :param pofile_suffix: String to append to the URL when linking
            to a `POFile`.
        """
        assert pofiles, "Empty POFiles list in reviewable target."
        first_pofile = pofiles[0]

        if len(pofiles) == 1:
            # Simple case: one translation file.  Go straight to
            # translation page for its unreviewed strings.
            return self._composePOFileLinks(pofiles, pofile_suffix)

        templates = set(pofile.potemplate for pofile in pofiles)

        productseries = set(
            template.productseries
            for template in templates
            if template.productseries)

        products = set(series.product for series in productseries)

        sourcepackagenames = set(
            template.sourcepackagename
            for template in templates
            if template.sourcepackagename)
        
        distroseries = set(
            template.distroseries
            for template in templates
            if template.distroseries)

        assert len(products) <= 1, "Got more than one product."
        assert len(sourcepackagenames) <= 1, "Got more than one package."
        assert len(distroseries) <= 1, "Got more than one distroseries."
        assert len(products) + len(sourcepackagenames) == 1, (
            "Didn't get POFiles for exactly one package or one product.")
        
        first_template = first_pofile.potemplate

        if len(templates) == 1:
            # Multiple translations for one template.  Link to the
            # template.
            return [canonical_url(first_template)]

        if sourcepackagenames:
            # Multiple POFiles for a source package.  Show its template
            # listing.
            distroseries = first_template.distroseries
            packagename = first_template.sourcepackagename
            return [canonical_url(distroseries.getSourcePackage(packagename))]

        if len(productseries) == 1:
            series = first_template.productseries
            # All for the same ProductSeries.
            languages = set(pofile.language for pofile in pofiles)
            if len(languages) == 1:
                # All for the same language in the same ProductSeries,
                # but apparently for different templates.  Link to
                # ProductSeriesLanguage.
                productserieslanguage = ProductSeriesLanguage(
                    series, pofiles[0].language)
                return [canonical_url(productserieslanguage)]
            else:
                # Multiple templates and languages in the same product
                # series.  Show its templates listing.
                return [canonical_url(series)]

        # Different release series of the same product.  Link to each of
        # the individual POFiles.
        return self._composePOFileLinks(pofiles, pofile_suffix)

    def _describeTarget(self, target, link, strings_count):
        """Produce a dict to describe a target and what it needs.

        :param target: Either a `Product` or a tuple of
            `SourcePackageName` and `DistroSeries`.
        :param link: URL for the relevant translations of `target`.
        :param strings_count: The number of strings that need work
            (which will be either review or translation).
        """
        if isinstance(target, tuple):
            (name, distroseries) = target
            target = distroseries.getSourcePackage(name)
            is_product = False
        else:
            is_product = True

        if strings_count == 1:
            strings_wording = '%d string'
        else:
            strings_wording = '%d strings'

        return {
            'target': target,
            'count': strings_count,
            'link': link,
            'count_wording': strings_wording % strings_count,
            'is_product': is_product,
        }

    def _setHistoryHorizon(self):
        """If not already set, set `self.history_horizon`."""
        if self.history_horizon is None:
            now = datetime.now(pytz.timezone('UTC'))
            self.history_horizon = now - timedelta(90, 0, 0)

    def _aggregateTranslationTargets(self, pofiles, pofile_link_suffix,
                                     count_pofile_strings):
        """Aggregate list of `POFile`s into sensible targets.

        Returns a list of target descriptions as returned by
        `_describeTarget` after going through `_findBestCommonLinks`.

        :param pofiles: A list of `POFile`s to aggregate.
        :param pofile_link_suffix: String to append to URLs when linking
            to POFiles.
        :param count_pofile_strings: Callable that returns the number of
            strings that need work for a given POFile.
        """
        targets = {}
        for pofile in pofiles:
            template = pofile.potemplate
            if template.productseries:
                target = template.productseries.product
            else:
                target = (template.sourcepackagename, template.distroseries)

            if target in targets:
                (count, target_pofiles) = targets[target]
            else:
                count = 0
                target_pofiles = []

            count += count_pofile_strings(pofile)
            target_pofiles.append(pofile)

            targets[target] = (count, target_pofiles)

        result = []
        for target, stats in targets.iteritems():
            (count, target_pofiles) = stats
            links = self._findBestCommonLinks(
                target_pofiles, pofile_link_suffix)
            for link in links:
                result.append(
                    self._describeTarget(target, link, count))

        return result

    @cachedproperty
    def all_projects_and_packages_to_review(self):
        """Top projects and packages for this person to review."""
        self._setHistoryHorizon()
        person = ITranslationsPerson(self.context)
        pofiles = person.getReviewableTranslationFiles(
            no_older_than=self.history_horizon)
        return self._aggregateTranslationTargets(
            pofiles, self._pofile_review_suffix, count_unreviewed)

    @property
    def top_projects_and_packages_to_review(self):
        """Suggest translations for this person to review."""
        self._setHistoryHorizon()

        # Maximum number of projects/packages to list that this person
        # has recently worked on.
        max_old_targets = 9
        # Length of overall list to display.
        list_length = 10

        # Start out with the translations that the person has recently
        # worked on.  Aggregation may reduce the number we get, so ask
        # the database for a few extra.
        fetch = 5 * max_old_targets
        recent = self.all_projects_and_packages_to_review[:fetch]

        # Fill out the list with other translations that the person
        # could also be reviewing.
        empty_slots = list_length - min(len(recent), max_old_targets)
        fetch = 5 * empty_slots

        person = ITranslationsPerson(self.context)
        pofiles = person.suggestReviewableTranslationFiles(
            no_older_than=self.history_horizon)[:fetch]
        random_suggestions = self._aggregateTranslationTargets(
            pofiles, self._pofile_review_suffix, count_unreviewed)

        return recent[:max_old_targets] + random_suggestions[:empty_slots]

    @cachedproperty
    def num_projects_and_packages_to_review(self):
        """How many translations do we suggest for reviewing?"""
        return len(self.all_projects_and_packages_to_review)

    def getTranslatableFiles(self, worst_first=False):
        """Find projects/packages this person could be translating."""
        self._setHistoryHorizon()
        pofiles = self.context.getFilesToTranslate(
            no_older_than=self.history_horizon, worst_first=worst_first)
        return self._aggregateTranslationTargets(
            pofiles, self._pofile_translate_suffix, count_untranslated)

    @property
    def person_includes_me(self):
        """Is the current user (a member of) this person?"""
        user = getUtility(ILaunchBag).user
        if user is None:
            return False
        else:
            return user.inTeam(self.context)


class PersonTranslationRelicensingView(LaunchpadFormView):
    """View for Person's translation relicensing page."""
    schema = ITranslationRelicensingAgreementEdit
    field_names = ['allow_relicensing', 'back_to']
    custom_widget(
        'allow_relicensing', LaunchpadRadioWidget, orientation='vertical')
    custom_widget('back_to', TextWidget, visible=False)

    @property
    def initial_values(self):
        """Set the default value for the relicensing radio buttons."""
        translations_person = ITranslationsPerson(self.context)
        # If the person has previously made a choice, we default to that.
        # Otherwise, we default to BSD, because that's what we'd prefer.
        if translations_person.translations_relicensing_agreement == False:
            default = TranslationRelicensingAgreementOptions.REMOVE
        else:
            default = TranslationRelicensingAgreementOptions.BSD
        return {
            "allow_relicensing": default,
            "back_to": self.request.get('back_to'),
            }

    @property
    def relicensing_url(self):
        """Return an URL for this view."""
        return canonical_url(self.context, view_name='+licensing')

    def getSafeRedirectURL(self, url):
        """Successful form submission should send to this URL."""
        if url and url.startswith(self.request.getApplicationURL()):
            return url
        else:
            return canonical_url(self.context)

    @action(_("Confirm"), name="submit")
    def submit_action(self, action, data):
        """Store person's decision about translations relicensing.

        Decision is stored through
        `ITranslationsPerson.translations_relicensing_agreement`
        which uses TranslationRelicensingAgreement table.
        """
        translations_person = ITranslationsPerson(self.context)
        allow_relicensing = data['allow_relicensing']
        if allow_relicensing == TranslationRelicensingAgreementOptions.BSD:
            translations_person.translations_relicensing_agreement = True
            self.request.response.addInfoNotification(_(
                "Thank you for BSD-licensing your translations."))
        elif (allow_relicensing ==
            TranslationRelicensingAgreementOptions.REMOVE):
            translations_person.translations_relicensing_agreement = False
            self.request.response.addInfoNotification(_(
                "We respect your choice. "
                "Your translations will be removed once we complete the "
                "switch to the BSD license. "
                "Thanks for trying out Launchpad Translations."))
        else:
            raise AssertionError(
                "Unknown allow_relicensing value: %r" % allow_relicensing)
        self.next_url = self.getSafeRedirectURL(data['back_to'])

