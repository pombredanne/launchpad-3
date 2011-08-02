# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test vocabulary adapters."""

__metaclass__ = type

from datetime import datetime
from urllib import urlencode

import pytz
import simplejson

from zope.app.form.interfaces import MissingInputError
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import ILaunchpadRoot
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.browser.vocabulary import IPickerEntry
from lp.app.errors import UnexpectedFormData
from lp.registry.interfaces.irc import IIrcIDSet
from lp.services.features.testing import FeatureFixture
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.views import create_view


class PersonPickerEntryAdapterTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_person_to_pickerentry(self):
        # IPerson can be adpated to IPickerEntry.
        person = self.factory.makePerson()
        adapter = IPickerEntry(person)
        self.assertTrue(IPickerEntry.providedBy(adapter))

    def test_PersonPickerEntryAdapter_email_anonymous(self):
        # Anonymous users cannot see entry email addresses.
        person = self.factory.makePerson(email='snarf@eg.dom')
        entry = IPickerEntry(person).getPickerEntry(None)
        self.assertEqual('<email address hidden>', entry.description)

    def test_PersonPickerEntryAdapter_visible_email_logged_in(self):
        # Logged in users can see visible email addresses.
        observer = self.factory.makePerson()
        login_person(observer)
        person = self.factory.makePerson(email='snarf@eg.dom')
        entry = IPickerEntry(person).getPickerEntry(None)
        self.assertEqual('snarf@eg.dom', entry.description)

    def test_PersonPickerEntryAdapter_hidden_email_logged_in(self):
        # Logged in users cannot see hidden email addresses.
        person = self.factory.makePerson(email='snarf@eg.dom')
        login_person(person)
        person.hide_email_addresses = True
        observer = self.factory.makePerson()
        login_person(observer)
        entry = IPickerEntry(person).getPickerEntry(None)
        self.assertEqual('<email address hidden>', entry.description)

    def test_PersonPickerEntryAdapter_no_email_logged_in(self):
        # Teams without email address have no desriptions.
        team = self.factory.makeTeam()
        observer = self.factory.makePerson()
        login_person(observer)
        entry = IPickerEntry(team).getPickerEntry(None)
        self.assertEqual(None, entry.description)

    def test_PersonPickerEntryAdapter_logged_in(self):
        # Logged in users can see visible email addresses.
        observer = self.factory.makePerson()
        login_person(observer)
        person = self.factory.makePerson(
            email='snarf@eg.dom', name='snarf')
        entry = IPickerEntry(person).getPickerEntry(None)
        self.assertEqual('sprite person', entry.css)
        self.assertEqual('sprite new-window', entry.link_css)

    def test_PersonPickerEntryAdapter_enhanced_picker_enabled_user(self):
        # The enhanced person picker provides more information for users.
        person = self.factory.makePerson(email='snarf@eg.dom', name='snarf')
        creation_date = datetime(
            2005, 01, 30, 0, 0, 0, 0, pytz.timezone('UTC'))
        removeSecurityProxy(person).datecreated = creation_date
        getUtility(IIrcIDSet).new(person, 'eg.dom', 'snarf')
        getUtility(IIrcIDSet).new(person, 'ex.dom', 'pting')
        entry = IPickerEntry(person).getPickerEntry(
            None, enhanced_picker_enabled=True)
        self.assertEqual('http://launchpad.dev/~snarf', entry.alt_title_link)
        self.assertEqual(
            ['snarf on eg.dom, pting on ex.dom', 'Member since 2005-01-30'],
            entry.details)

    def test_PersonPickerEntryAdapter_enhanced_picker_enabled_team(self):
        # The enhanced person picker provides more information for teams.
        team = self.factory.makeTeam(email='fnord@eg.dom', name='fnord')
        entry = IPickerEntry(team).getPickerEntry(
            None, enhanced_picker_enabled=True)
        self.assertEqual('http://launchpad.dev/~fnord', entry.alt_title_link)
        self.assertEqual(['Team members: 1'], entry.details)

    def test_PersonPickerEntryAdapter_enhanced_picker_enabled_badges(self):
        # The enhanced person picker provides affilliation information.
        person = self.factory.makePerson(email='snarf@eg.dom', name='snarf')
        project = self.factory.makeProduct(name='fnord', owner=person)
        bugtask = self.factory.makeBugTask(target=project)
        entry = IPickerEntry(person).getPickerEntry(
            bugtask, enhanced_picker_enabled=True)
        self.assertEqual(1, len(entry.badges))
        self.assertEqual('/@@/product-badge', entry.badges[0]['url'])
        self.assertEqual('Affiliated with Fnord', entry.badges[0]['alt'])


class HugeVocabularyJSONViewTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

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
        view = self.create_vocabulary_view({'name': 'ValidPerson'})
        self.assertRaisesWithContent(
            MissingInputError, "('search_text', '', None)", view.__call__)

    def test_vocabulary_name_unknown_error(self):
        form = dict(name='snarf', search_text='pting')
        view = self.create_vocabulary_view(form)
        self.assertRaisesWithContent(
            UnexpectedFormData, "Unknown vocabulary 'snarf'", view.__call__)

    def test_json_entries(self):
        feature_flag = {'disclosure.picker_enhancements.enabled': 'on'}
        flags = FeatureFixture(feature_flag)
        flags.setUp()
        self.addCleanup(flags.cleanUp)
        form = dict(name='ValidPersonOrTeam', search_text='guadamen')
        view = self.create_vocabulary_view(form)
        result = simplejson.loads(view())
        expected = {
            "alt_title": "guadamen",
            "alt_title_link": "http://launchpad.dev/~guadamen",
            "api_uri": "/~guadamen",
            "css": "sprite team",
            "details": ['Team members: 11'],
            "link_css": "sprite new-window",
            "metadata": "team",
            "title": "GuadaMen",
            "value": "guadamen"
            }
        self.assertTrue('entries' in result)
        self.assertContentEqual(
            expected.items(), result['entries'][0].items())

    def test_default_batch_size(self):
        form = dict(name='ValidPersonOrTeam', search_text='admin')
        view = self.create_vocabulary_view(form)
        result = simplejson.loads(view())
        self.assertEqual(6, result['total_size'])
        self.assertEqual(5, len(result['entries']))

    def test_batch_size(self):
        form = dict(
            name='ValidPersonOrTeam', search_text='admin',
            start='0', batch='1')
        view = self.create_vocabulary_view(form)
        result = simplejson.loads(view())
        self.assertEqual(6, result['total_size'])
        self.assertEqual(1, len(result['entries']))

    def test_start_and_offset(self):
        form = dict(
            name='ValidPersonOrTeam', search_text='admin',
            start='1', batch='1')
        view = self.create_vocabulary_view(form)
        result = simplejson.loads(view())
        self.assertEqual(6, result['total_size'])
        self.assertEqual(1, len(result['entries']))
        self.assertEqual('name16', result['entries'][0]['value'])
