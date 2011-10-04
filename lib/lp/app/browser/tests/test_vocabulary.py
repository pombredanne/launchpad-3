# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test vocabulary adapters."""

__metaclass__ = type

from datetime import datetime
from urllib import urlencode

import pytz
import simplejson
from zope.app.form.interfaces import MissingInputError
from zope.component import (
    getSiteManager,
    getUtility,
    )
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import ILaunchpadRoot
from canonical.launchpad.webapp.vocabulary import (
    CountableIterator,
    IHugeVocabulary,
    VocabularyFilter,
    )
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.app.browser.vocabulary import (
    IPickerEntrySource,
    MAX_DESCRIPTION_LENGTH,
    )
from lp.app.errors import UnexpectedFormData
from lp.registry.interfaces.irc import IIrcIDSet
from lp.registry.interfaces.series import SeriesStatus
from lp.services.features.testing import FeatureFixture
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.views import create_view


def get_picker_entry(item_subject, context_object, **kwargs):
    """Adapt `item_subject` to `IPickerEntrySource` and return its item."""
    [entry] = IPickerEntrySource(item_subject).getPickerEntries(
        [item_subject], context_object, **kwargs)
    return entry


class DefaultPickerEntrySourceAdapterTestCase(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_css_image_entry_without_icon(self):
        # When the context does not have a custom icon, its sprite is used.
        product = self.factory.makeProduct()
        entry = get_picker_entry(product, object())
        self.assertEqual("sprite product", entry.css)
        self.assertEqual(None, entry.image)

    def test_css_image_entry_without_icon_or_sprite(self):
        # When the context does not have a custom icon, and there is no
        # sprite adapter rules, the generic sprite is used.
        thing = object()
        entry = get_picker_entry(thing, object())
        self.assertEqual('sprite bullet', entry.css)
        self.assertEqual(None, entry.image)

    def test_css_image_entry_with_icon(self):
        # When the context has a custom icon the URL is used.
        icon = self.factory.makeLibraryFileAlias(
            filename='smurf.png', content_type='image/png')
        product = self.factory.makeProduct(icon=icon)
        entry = get_picker_entry(product, object())
        self.assertEqual(None, entry.css)
        self.assertEqual(icon.getURL(), entry.image)


class PersonPickerEntrySourceAdapterTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_person_to_pickerentry(self):
        # IPerson can be adpated to IPickerEntry.
        person = self.factory.makePerson()
        adapter = IPickerEntrySource(person)
        self.assertTrue(IPickerEntrySource.providedBy(adapter))

    def test_PersonPickerEntrySourceAdapter_email_anonymous(self):
        # Anonymous users cannot see entry email addresses.
        person = self.factory.makePerson(email='snarf@eg.dom')
        self.assertEqual(
            "<email address hidden>",
            get_picker_entry(person, None).description)

    def test_PersonPickerEntrySourceAdapter_visible_email_logged_in(self):
        # Logged in users can see visible email addresses.
        observer = self.factory.makePerson()
        login_person(observer)
        person = self.factory.makePerson(email='snarf@eg.dom')
        self.assertEqual(
            'snarf@eg.dom', get_picker_entry(person, None).description)

    def test_PersonPickerEntrySourceAdapter_hidden_email_logged_in(self):
        # Logged in users cannot see hidden email addresses.
        person = self.factory.makePerson(email='snarf@eg.dom')
        login_person(person)
        person.hide_email_addresses = True
        observer = self.factory.makePerson()
        login_person(observer)
        self.assertEqual(
            "<email address hidden>",
            get_picker_entry(person, None).description)

    def test_PersonPickerEntrySourceAdapter_no_email_logged_in(self):
        # Teams without email address have no desriptions.
        team = self.factory.makeTeam()
        observer = self.factory.makePerson()
        login_person(observer)
        self.assertEqual(None, get_picker_entry(team, None).description)

    def test_PersonPickerEntrySourceAdapter_logged_in(self):
        # Logged in users can see visible email addresses.
        observer = self.factory.makePerson()
        login_person(observer)
        person = self.factory.makePerson(
            email='snarf@eg.dom', name='snarf')
        entry = get_picker_entry(person, None)
        self.assertEqual('sprite person', entry.css)
        self.assertEqual('sprite new-window', entry.link_css)

    def test_PersonPickerEntrySourceAdapter_enhanced_picker_user(self):
        # The enhanced person picker provides more information for users.
        person = self.factory.makePerson(email='snarf@eg.dom', name='snarf')
        creation_date = datetime(
            2005, 01, 30, 0, 0, 0, 0, pytz.timezone('UTC'))
        removeSecurityProxy(person).datecreated = creation_date
        getUtility(IIrcIDSet).new(person, 'eg.dom', 'snarf')
        getUtility(IIrcIDSet).new(person, 'ex.dom', 'pting')
        entry = get_picker_entry(
            person, None, enhanced_picker_enabled=True,
            picker_expander_enabled=True)
        self.assertEqual('http://launchpad.dev/~snarf', entry.alt_title_link)
        self.assertEqual(
            ['snarf on eg.dom, pting on ex.dom', 'Member since 2005-01-30'],
            entry.details)

    def test_PersonPickerEntrySourceAdapter_enhanced_picker_team(self):
        # The enhanced person picker provides more information for teams.
        team = self.factory.makeTeam(email='fnord@eg.dom', name='fnord')
        entry = get_picker_entry(
            team, None, enhanced_picker_enabled=True,
            picker_expander_enabled=True)
        self.assertEqual('http://launchpad.dev/~fnord', entry.alt_title_link)
        self.assertEqual(['Team members: 1'], entry.details)

    def test_PersonPickerEntryAdapter_enhanced_picker_enabled_badges(self):
        # The enhanced person picker provides affiliation information.
        person = self.factory.makePerson(email='snarf@eg.dom', name='snarf')
        project = self.factory.makeProduct(
            name='fnord', owner=person, bug_supervisor=person)
        bugtask = self.factory.makeBugTask(target=project)
        entry = get_picker_entry(
            person, bugtask, enhanced_picker_enabled=True,
            picker_expander_enabled=True,
            personpicker_affiliation_enabled=True)
        self.assertEqual(3, len(entry.badges))
        self.assertEqual('/@@/product-badge', entry.badges[0]['url'])
        self.assertEqual('Fnord', entry.badges[0]['label'])
        self.assertEqual('maintainer', entry.badges[0]['role'])
        self.assertEqual('/@@/product-badge', entry.badges[1]['url'])
        self.assertEqual('Fnord', entry.badges[1]['label'])
        self.assertEqual('driver', entry.badges[1]['role'])
        self.assertEqual('/@@/product-badge', entry.badges[2]['url'])
        self.assertEqual('Fnord', entry.badges[2]['label'])
        self.assertEqual('bug supervisor', entry.badges[2]['role'])

    def test_PersonPickerEntryAdapter_badges_without_IHasAffiliation(self):
        # The enhanced person picker handles objects that do not support
        # IHasAffilliation.
        person = self.factory.makePerson(email='snarf@eg.dom', name='snarf')
        thing = object()
        entry = get_picker_entry(
            person, thing, enhanced_picker_enabled=True,
            picker_expander_enabled=True,
            personpicker_affiliation_enabled=True)
        self.assertIsNot(None, entry)


class TestDistributionSourcePackagePickerEntrySourceAdapter(
        TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistributionSourcePackagePickerEntrySourceAdapter,
              self).setUp()
        flag = {'disclosure.target_picker_enhancements.enabled': 'on'}
        self.useFixture(FeatureFixture(flag))

    def getPickerEntry(self, dsp):
        return get_picker_entry(dsp, object())

    def test_dsp_to_picker_entry(self):
        dsp = self.factory.makeDistributionSourcePackage()
        adapter = IPickerEntrySource(dsp)
        self.assertTrue(IPickerEntrySource.providedBy(adapter))

    def test_dsp_target_type(self):
        dsp = self.factory.makeDistributionSourcePackage()
        series = self.factory.makeDistroSeries(distribution=dsp.distribution)
        release = self.factory.makeSourcePackageRelease(
            distroseries=series,
            sourcepackagename=dsp.sourcepackagename)
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=series,
            sourcepackagerelease=release)
        self.assertEqual('package', self.getPickerEntry(dsp).target_type)

    def test_dsp_provides_details(self):
        dsp = self.factory.makeDistributionSourcePackage()
        series = self.factory.makeDistroSeries(distribution=dsp.distribution)
        release = self.factory.makeSourcePackageRelease(
            distroseries=series,
            sourcepackagename=dsp.sourcepackagename)
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=series,
            sourcepackagerelease=release)
        self.assertEqual(
            "Maintainer: %s" % dsp.currentrelease.maintainer.displayname,
            self.getPickerEntry(dsp).details[0])

    def test_dsp_provides_summary(self):
        dsp = self.factory.makeDistributionSourcePackage()
        series = self.factory.makeDistroSeries(distribution=dsp.distribution)
        release = self.factory.makeSourcePackageRelease(
            distroseries=series,
            sourcepackagename=dsp.sourcepackagename)
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=series,
            sourcepackagerelease=release)
        self.assertEqual(
            "Not yet built.", self.getPickerEntry(dsp).description)

        archseries = self.factory.makeDistroArchSeries(distroseries=series)
        bpn = self.factory.makeBinaryPackageName(name='fnord')
        self.factory.makeBinaryPackagePublishingHistory(
            binarypackagename=bpn,
            source_package_release=release,
            sourcepackagename=dsp.sourcepackagename,
            distroarchseries=archseries)
        self.assertEqual("fnord", self.getPickerEntry(dsp).description)

    def test_dsp_alt_title_is_none(self):
        # DSP titles are contructed from the distro and package Launchapd Ids,
        # alt_titles are redundant because they are also Launchpad Ids.
        distro = self.factory.makeDistribution(name='fnord')
        series = self.factory.makeDistroSeries(
            name='pting', distribution=distro)
        self.factory.makeSourcePackage(
            sourcepackagename='snarf', distroseries=series, publish=True)
        dsp = distro.getSourcePackage('snarf')
        self.assertEqual(None, self.getPickerEntry(dsp).alt_title)

    def test_dsp_provides_alt_title_link(self):
        distro = self.factory.makeDistribution(name='fnord')
        series = self.factory.makeDistroSeries(
            name='pting', distribution=distro)
        self.factory.makeSourcePackage(
            sourcepackagename='snarf', distroseries=series, publish=True)
        dsp = distro.getSourcePackage('snarf')
        self.assertEqual(
            'http://launchpad.dev/fnord/+source/snarf',
            self.getPickerEntry(dsp).alt_title_link)


class TestProductPickerEntrySourceAdapter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductPickerEntrySourceAdapter, self).setUp()
        flag = {'disclosure.target_picker_enhancements.enabled': 'on'}
        self.useFixture(FeatureFixture(flag))

    def getPickerEntry(self, product):
        return get_picker_entry(product, object())

    def test_product_to_picker_entry(self):
        product = self.factory.makeProduct()
        adapter = IPickerEntrySource(product)
        self.assertTrue(IPickerEntrySource.providedBy(adapter))

    def test_product_provides_alt_title(self):
        product = self.factory.makeProduct()
        self.assertEqual(product.name, self.getPickerEntry(product).alt_title)

    def test_product_target_type(self):
        product = self.factory.makeProduct()
        # We check for project, not product, because users don't see
        # products.
        self.assertEqual('project', self.getPickerEntry(product).target_type)

    def test_product_provides_details(self):
        product = self.factory.makeProduct()
        self.assertEqual(
            "Maintainer: %s" % product.owner.displayname,
            self.getPickerEntry(product).details[0])

    def test_product_provides_summary(self):
        product = self.factory.makeProduct()
        self.assertEqual(
            product.summary, self.getPickerEntry(product).description)

    def test_product_truncates_summary(self):
        summary = ("This is a deliberately, overly long summary. It goes on"
                   "and on and on so as to break things up a good bit.")
        product = self.factory.makeProduct(summary=summary)
        index = summary.rfind(' ', 0, 45)
        expected_summary = summary[:index + 1]
        expected_details = summary[index:]
        entry = self.getPickerEntry(product)
        self.assertEqual(
            expected_summary, entry.description)
        self.assertEqual(
            expected_details, entry.details[0])

    def test_product_provides_alt_title_link(self):
        product = self.factory.makeProduct(name='fnord')
        self.assertEqual(
            'http://launchpad.dev/fnord',
            self.getPickerEntry(product).alt_title_link)


class TestProjectGroupPickerEntrySourceAdapter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProjectGroupPickerEntrySourceAdapter, self).setUp()
        flag = {'disclosure.target_picker_enhancements.enabled': 'on'}
        self.useFixture(FeatureFixture(flag))

    def getPickerEntry(self, projectgroup):
        return get_picker_entry(projectgroup, object())

    def test_projectgroup_to_picker_entry(self):
        projectgroup = self.factory.makeProject()
        adapter = IPickerEntrySource(projectgroup)
        self.assertTrue(IPickerEntrySource.providedBy(adapter))

    def test_projectgroup_provides_alt_title(self):
        projectgroup = self.factory.makeProject()
        self.assertEqual(
            projectgroup.name, self.getPickerEntry(projectgroup).alt_title)

    def test_projectgroup_target_type(self):
        projectgroup = self.factory.makeProject()
        self.assertEqual(
            'project group', self.getPickerEntry(projectgroup).target_type)

    def test_projectgroup_provides_details(self):
        projectgroup = self.factory.makeProject()
        self.assertEqual(
            "Maintainer: %s" % projectgroup.owner.displayname,
            self.getPickerEntry(projectgroup).details[0])

    def test_projectgroup_provides_summary(self):
        projectgroup = self.factory.makeProject()
        self.assertEqual(
            projectgroup.summary,
            self.getPickerEntry(projectgroup).description)

    def test_projectgroup_truncates_summary(self):
        summary = ("This is a deliberately, overly long summary. It goes on"
                   "and on and on so as to break things up a good bit.")
        projectgroup = self.factory.makeProject(summary=summary)
        index = summary.rfind(' ', 0, 45)
        expected_summary = summary[:index + 1]
        expected_details = summary[index:]
        entry = self.getPickerEntry(projectgroup)
        self.assertEqual(
            expected_summary, entry.description)
        self.assertEqual(
            expected_details, entry.details[0])

    def test_projectgroup_provides_alt_title_link(self):
        projectgroup = self.factory.makeProject(name='fnord')
        self.assertEqual(
            'http://launchpad.dev/fnord',
            self.getPickerEntry(projectgroup).alt_title_link)


class TestDistributionPickerEntrySourceAdapter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistributionPickerEntrySourceAdapter, self).setUp()
        flag = {'disclosure.target_picker_enhancements.enabled': 'on'}
        self.useFixture(FeatureFixture(flag))

    def getPickerEntry(self, distribution):
        return get_picker_entry(distribution, object())

    def test_distribution_to_picker_entry(self):
        distribution = self.factory.makeDistribution()
        adapter = IPickerEntrySource(distribution)
        self.assertTrue(IPickerEntrySource.providedBy(adapter))

    def test_distribution_provides_alt_title(self):
        distribution = self.factory.makeDistribution()
        self.assertEqual(
            distribution.name, self.getPickerEntry(distribution).alt_title)

    def test_distribution_provides_details(self):
        distribution = self.factory.makeDistribution()
        self.factory.makeDistroSeries(
            distribution=distribution, status=SeriesStatus.CURRENT)
        self.assertEqual(
            "Maintainer: %s" % distribution.currentseries.owner.displayname,
            self.getPickerEntry(distribution).details[0])

    def test_distribution_provides_summary(self):
        distribution = self.factory.makeDistribution()
        self.assertEqual(
            distribution.summary,
            self.getPickerEntry(distribution).description)

    def test_distribution_target_type(self):
        distribution = self.factory.makeDistribution()
        self.assertEqual(
            'distribution', self.getPickerEntry(distribution).target_type)

    def test_distribution_truncates_summary(self):
        summary = (
            "This is a deliberately, overly long summary. It goes on "
            "and on and on so as to break things up a good bit.")
        distribution = self.factory.makeDistribution(summary=summary)
        index = summary.rfind(' ', 0, 45)
        expected_summary = summary[:index + 1]
        expected_details = summary[index:]
        entry = self.getPickerEntry(distribution)
        self.assertEqual(
            expected_summary, entry.description)
        self.assertEqual(
            expected_details, entry.details[0])

    def test_distribution_provides_alt_title_link(self):
        distribution = self.factory.makeDistribution(name='fnord')
        self.assertEqual(
            'http://launchpad.dev/fnord',
            self.getPickerEntry(distribution).alt_title_link)


class TestPersonVocabulary:
    implements(IHugeVocabulary)
    test_persons = []

    @classmethod
    def setTestData(cls, person_list):
        cls.test_persons = person_list

    def __init__(self, context):
        self.context = context

    def toTerm(self, person):
        return SimpleTerm(person, person.name, person.displayname)

    def searchForTerms(self, query=None, vocab_filter=None):
        if vocab_filter is None:
            filter_term = ''
        else:
            filter_term = vocab_filter.filter_terms[0]
        found = [
            person for person in self.test_persons
                if query in person.name and filter_term in person.name]
        return CountableIterator(len(found), found, self.toTerm)


class TestVocabularyFilter(VocabularyFilter):
    # A filter returning all objects.

    def __new__(cls):
        return super(VocabularyFilter, cls).__new__(
            cls, 'FILTER', 'Test Filter', 'Test')

    @property
    def filter_terms(self):
        return ['xpting-person']


class HugeVocabularyJSONViewTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(HugeVocabularyJSONViewTestCase, self).setUp()
        test_persons = []
        for name in range(1, 7):
            test_persons.append(
                self.factory.makePerson(name='pting-%s' % name))
        TestPersonVocabulary.setTestData(test_persons)
        getSiteManager().registerUtility(
            TestPersonVocabulary, IVocabularyFactory, 'TestPerson')
        self.addCleanup(
            getSiteManager().unregisterUtility,
            TestPersonVocabulary, IVocabularyFactory, 'TestPerson')
        self.addCleanup(TestPersonVocabulary.setTestData, [])

    @staticmethod
    def create_vocabulary_view(form, context=None):
        if context is None:
            context = getUtility(ILaunchpadRoot)
        query_string = urlencode(form)
        return create_view(
            context, '+huge-vocabulary', form=form, query_string=query_string)

    def test_name_field_missing_error(self):
        view = self.create_vocabulary_view({})
        self.assertRaisesWithContent(
            MissingInputError, "('name', '', None)", view.__call__)

    def test_search_text_field_missing_error(self):
        view = self.create_vocabulary_view({'name': 'TestPerson'})
        self.assertRaisesWithContent(
            MissingInputError, "('search_text', '', None)", view.__call__)

    def test_vocabulary_name_unknown_error(self):
        form = dict(name='snarf', search_text='pting')
        view = self.create_vocabulary_view(form)
        self.assertRaisesWithContent(
            UnexpectedFormData, "Unknown vocabulary 'snarf'", view.__call__)

    def test_json_entries(self):
        # The results are JSON encoded.
        feature_flag = {
            'disclosure.picker_enhancements.enabled': 'on',
            'disclosure.picker_expander.enabled': 'on',
            'disclosure.personpicker_affiliation.enabled': 'on',
            }
        flags = FeatureFixture(feature_flag)
        flags.setUp()
        self.addCleanup(flags.cleanUp)
        team = self.factory.makeTeam(name='xpting-team')
        person = self.factory.makePerson(name='xpting-person')
        creation_date = datetime(
            2005, 01, 30, 0, 0, 0, 0, pytz.timezone('UTC'))
        removeSecurityProxy(person).datecreated = creation_date
        TestPersonVocabulary.test_persons.extend([team, person])
        product = self.factory.makeProduct(owner=team)
        bugtask = self.factory.makeBugTask(target=product)
        form = dict(name='TestPerson', search_text='xpting')
        view = self.create_vocabulary_view(form, context=bugtask)
        result = simplejson.loads(view())
        expected = [{
            "alt_title": team.name,
            "alt_title_link": "http://launchpad.dev/~%s" % team.name,
            "api_uri": "/~%s" % team.name,
            "badges":
                [{"label": product.displayname,
                  "role": "maintainer",
                  "url": "/@@/product-badge"},
                {"label": product.displayname,
                 "role": "driver",
                  "url": "/@@/product-badge"}],
            "css": "sprite team",
            "details": ['Team members: 1'],
            "link_css": "sprite new-window",
            "metadata": "team",
            "title": team.displayname,
            "value": team.name
            },
            {
            "alt_title": person.name,
            "alt_title_link": "http://launchpad.dev/~%s" % person.name,
            "api_uri": "/~%s" % person.name,
            "css": "sprite person",
            "description": "<email address hidden>",
            "details": ['Member since 2005-01-30'],
            "link_css": "sprite new-window",
            "metadata": "person",
            "title": person.displayname,
            "value": person.name
            }]
        self.assertTrue('entries' in result)
        self.assertContentEqual(
            expected[0].items(), result['entries'][0].items())
        self.assertContentEqual(
            expected[1].items(), result['entries'][1].items())

    def test_vocab_filter(self):
        # The vocab filter is used to filter results.
        team = self.factory.makeTeam(name='xpting-team')
        person = self.factory.makePerson(name='xpting-person')
        TestPersonVocabulary.test_persons.extend([team, person])
        product = self.factory.makeProduct(owner=team)
        vocab_filter = TestVocabularyFilter()
        form = dict(name='TestPerson',
                    search_text='xpting', search_filter=vocab_filter)
        view = self.create_vocabulary_view(form, context=product)
        result = simplejson.loads(view())
        entries = result['entries']
        self.assertEqual(1, len(entries))
        self.assertEqual('xpting-person', entries[0]['value'])

    def test_max_description_size(self):
        # Descriptions over 120 characters are truncated and ellipsised.
        email = 'pting-' * 19 + '@example.dom'
        person = self.factory.makePerson(name='pting-n', email=email)
        TestPersonVocabulary.test_persons.append(person)
        # Login to gain permission to know the email address that used
        # for the description
        login_person(person)
        form = dict(name='TestPerson', search_text='pting-n')
        view = self.create_vocabulary_view(form)
        result = simplejson.loads(view())
        expected = (email[:MAX_DESCRIPTION_LENGTH - 3] + '...')
        self.assertEqual(
            'pting-n', result['entries'][0]['value'])
        self.assertEqual(
            expected, result['entries'][0]['description'])

    def test_default_batch_size(self):
        # The results are batched.
        form = dict(name='TestPerson', search_text='pting')
        view = self.create_vocabulary_view(form)
        result = simplejson.loads(view())
        total_size = result['total_size']
        entries = len(result['entries'])
        self.assertTrue(
            total_size > entries,
            'total_size: %d is less than entries: %d' % (total_size, entries))

    def test_batch_size(self):
        # A The batch size can be specified with the batch param.
        form = dict(
            name='TestPerson', search_text='pting',
            start='0', batch='1')
        view = self.create_vocabulary_view(form)
        result = simplejson.loads(view())
        self.assertEqual(6, result['total_size'])
        self.assertEqual(1, len(result['entries']))

    def test_start_offset(self):
        # The offset of the batch is specified with the start param.
        form = dict(
            name='TestPerson', search_text='pting',
            start='1', batch='1')
        view = self.create_vocabulary_view(form)
        result = simplejson.loads(view())
        self.assertEqual(6, result['total_size'])
        self.assertEqual(1, len(result['entries']))
        self.assertEqual('pting-2', result['entries'][0]['value'])
