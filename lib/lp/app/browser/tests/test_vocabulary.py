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
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.browser.vocabulary import (
    IPickerEntrySource,
    MAX_DESCRIPTION_LENGTH,
    )
from lp.app.errors import UnexpectedFormData
from lp.registry.interfaces.irc import IIrcIDSet
from lp.services.features.testing import FeatureFixture
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.views import create_view


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
        [entry] = IPickerEntrySource(person).getPickerEntries([person], None)
        self.assertEqual('<email address hidden>', entry.description)

    def test_PersonPickerEntrySourceAdapter_visible_email_logged_in(self):
        # Logged in users can see visible email addresses.
        observer = self.factory.makePerson()
        login_person(observer)
        person = self.factory.makePerson(email='snarf@eg.dom')
        [entry] = IPickerEntrySource(person).getPickerEntries([person], None)
        self.assertEqual('snarf@eg.dom', entry.description)

    def test_PersonPickerEntrySourceAdapter_hidden_email_logged_in(self):
        # Logged in users cannot see hidden email addresses.
        person = self.factory.makePerson(email='snarf@eg.dom')
        login_person(person)
        person.hide_email_addresses = True
        observer = self.factory.makePerson()
        login_person(observer)
        [entry] = IPickerEntrySource(person).getPickerEntries([person], None)
        self.assertEqual('<email address hidden>', entry.description)

    def test_PersonPickerEntrySourceAdapter_no_email_logged_in(self):
        # Teams without email address have no desriptions.
        team = self.factory.makeTeam()
        observer = self.factory.makePerson()
        login_person(observer)
        [entry] = IPickerEntrySource(team).getPickerEntries([team], None)
        self.assertEqual(None, entry.description)

    def test_PersonPickerEntrySourceAdapter_logged_in(self):
        # Logged in users can see visible email addresses.
        observer = self.factory.makePerson()
        login_person(observer)
        person = self.factory.makePerson(
            email='snarf@eg.dom', name='snarf')
        [entry] = IPickerEntrySource(person).getPickerEntries([person], None)
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
        [entry] = IPickerEntrySource(person).getPickerEntries(
            [person], None, enhanced_picker_enabled=True,
            picker_expander_enabled=True)
        self.assertEqual('http://launchpad.dev/~snarf', entry.alt_title_link)
        self.assertEqual(
            ['snarf on eg.dom, pting on ex.dom', 'Member since 2005-01-30'],
            entry.details)

    def test_PersonPickerEntrySourceAdapter_enhanced_picker_team(self):
        # The enhanced person picker provides more information for teams.
        team = self.factory.makeTeam(email='fnord@eg.dom', name='fnord')
        [entry] = IPickerEntrySource(team).getPickerEntries(
            [team], None, enhanced_picker_enabled=True,
            picker_expander_enabled=True)
        self.assertEqual('http://launchpad.dev/~fnord', entry.alt_title_link)
        self.assertEqual(['Team members: 1'], entry.details)

    def test_PersonPickerEntryAdapter_enhanced_picker_enabled_badges(self):
        # The enhanced person picker provides affiliation information.
        person = self.factory.makePerson(email='snarf@eg.dom', name='snarf')
        project = self.factory.makeProduct(
            name='fnord', owner=person, bug_supervisor=person)
        bugtask = self.factory.makeBugTask(target=project)
        [entry] = IPickerEntrySource(person).getPickerEntries(
            [person], bugtask, enhanced_picker_enabled=True,
            picker_expander_enabled=True,
            personpicker_affiliation_enabled=True)
        self.assertEqual(3, len(entry.badges))
        self.assertEqual('/@@/product-badge', entry.badges[0]['url'])
        self.assertEqual('Fnord maintainer', entry.badges[0]['alt'])
        self.assertEqual('/@@/product-badge', entry.badges[1]['url'])
        self.assertEqual('Fnord driver', entry.badges[1]['alt'])
        self.assertEqual('/@@/product-badge', entry.badges[2]['url'])
        self.assertEqual('Fnord bug supervisor', entry.badges[2]['alt'])

    def test_PersonPickerEntryAdapter_badges_without_IHasAffiliation(self):
        # The enhanced person picker handles objects that do not support
        # IHasAffilliation.
        person = self.factory.makePerson(email='snarf@eg.dom', name='snarf')
        thing = object()
        [entry] = IPickerEntrySource(person).getPickerEntries(
            [person], thing, enhanced_picker_enabled=True,
            picker_expander_enabled=True,
            personpicker_affiliation_enabled=True)
        self.assertEqual(None, None)


class TestDistributionSourcePackagePickerEntrySourceAdapter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_dsp_to_picker_entry(self):
        # IPerson can be adpated to IPickerEntry.
        dsp = self.factory.makeDistributionSourcePackage()
        adapter = IPickerEntrySource(dsp)
        self.assertTrue(IPickerEntrySource.providedBy(adapter))


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
                [{"alt": "%s maintainer" % product.displayname,
                  "url": "/@@/product-badge"},
                {"alt": "%s driver" % product.displayname,
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
