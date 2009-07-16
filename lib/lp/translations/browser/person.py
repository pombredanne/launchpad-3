# Copyright 2009 Canonical Ltd

"""Person-related translations view classes."""

__metaclass__ = type

__all__ = [
    'PersonTranslationView',
    'PersonTranslationRelicensingView',
]

import urllib
from zope.app.form.browser import TextWidget
from zope.component import getUtility

from canonical.launchpad import _
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
        return bool(self.translation_groups)

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

    def _findBestCommonReviewLinks(self, pofiles):
        """Find best links to a bunch of related `POFile`s.

        The `POFile`s must either be in the same `Product`, or in the
        same `DistroSeries` and `SourcePackageName`.
        
        This method finds the greatest common denominators between them,
        and returns a list of links to them: the individual translation
        if there is only one, the template if multiple translations of
        one template are involved, and so on.
        """
        assert pofiles, "Empty POFiles list in reviewable target."
        first_pofile = pofiles[0]

        if len(pofiles) == 1:
            # Simple case: one translation file.  Go straight to
            # translation page for its unreviewed strings.
            return [
                canonical_url(first_pofile) +
                "/+translate?show=new_suggestions"]

        productseries = set(
            pofile.potemplate.productseries
            for pofile in pofiles
            if pofile.potemplate.productseries)

        first_template = first_pofile.potemplate
        if first_template.sourcepackagename:
            # Multiple POFiles for a source package.  Show its template
            # listing.
            assert not productseries, "Found POFiles for mixed targets."
            distroseries = first_template.distroseries
            packagename = first_template.sourcepackagename
            return [canonical_url(distroseries.getSourcePackage(packagename))]

        if len(productseries) == 1:
            # All for the same ProductSeries.  Show its template
            # listing.
            return [canonical_url(first_template.productseries)]

        # Different release series of the same product.  Link to each of
        # the individual POFiles.
        return pofiles

    def _describeReviewableTarget(self, target, link, strings_count):
        """Produce dict to describe a reviewable target.

        The target may be a `Product` or a tuple of `SourcePackageName`
        and `DistroSeries`.
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

    def _aggregateTranslationTargets(self, pofiles):
        """Aggregate list of `POFile`s into sensible targets.

        Returns a list of target descriptions as returned by
        `_describeReviewableTarget` after going through
        `_findBestCommonReviewLinks`.
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

            (imported, changed, rosetta, unreviewed) = pofile.getStatistics()
            count += unreviewed
            target_pofiles.append(pofile)

            targets[target] = (count, target_pofiles)

        result = []
        for target, stats in targets.iteritems():
            (count, target_pofiles) = stats
            links = self._findBestCommonReviewLinks(target_pofiles)
            for link in links:
                result.append(
                    self._describeReviewableTarget(target, link, count))

        return result

    @cachedproperty
    def all_projects_and_packages_to_review(self):
        """Top projects and packages for this person to review."""
        self._setHistoryHorizon()
        return self._aggregateTranslationTargets(
            self.context.getReviewableTranslationFiles(
                no_older_than=self.history_horizon))

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
        random_suggestions = self._aggregateTranslationTargets(
            self.context.suggestReviewableTranslationFiles(
                no_older_than=self.history_horizon)[:fetch])

        return recent[:max_old_targets] + random_suggestions[:empty_slots]

    @cachedproperty
    def num_projects_and_packages_to_review(self):
        """How many translations do we suggest for reviewing?"""
        return len(self.all_projects_and_packages_to_review)

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

