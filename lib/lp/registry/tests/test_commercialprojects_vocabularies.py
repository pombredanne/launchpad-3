# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the commercial projects vocabularies."""

__metaclass__ = type

from lp.app.browser.tales import DateTimeFormatterAPI
from lp.registry.interfaces.product import (
    License,
    )
from lp.registry.vocabularies import CommercialProjectsVocabulary
from lp.services.identity.interfaces.emailaddress import EmailAddressStatus
from lp.testing import (
    celebrity_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestCommProjVocabulary(TestCaseWithFactory):
    """Test that the CommercialProjectsVocabulary behaves as expected."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestCommProjVocabulary, self).setUp()
        self.owner = self.factory.makePerson(
            email_address_status=EmailAddressStatus.VALIDATED)
        self._createProjects()
        self.vocab = CommercialProjectsVocabulary(context=self.owner)

    def _createProjects(self):
        """Create maintained projects."""
        # Create 5 proprietary projects.
        self.num_proprietary = 5
        for i in range(self.num_proprietary):
            self.factory.makeProduct(
                name='widget%d' % i, owner=self.owner,
                 licenses=[License.OTHER_PROPRIETARY])
        # Create an open source project.
        self.num_commercial = self.num_proprietary + 1
        self.maintained_project = self.factory.makeProduct(
            name='open-widget', owner=self.owner,
            licenses=[License.GNU_GPL_V3])
        # Create a deactivated open source project.
        with celebrity_logged_in('admin'):
            self.deactivated_project = self.factory.makeProduct(
                name='norwegian-blue-widget', owner=self.owner,
                licenses=[License.GNU_GPL_V3])
            self.deactivated_project.active = False

    def test_attributes(self):
        self.assertEqual('Select a commercial project', self.vocab.displayname)
        self.assertEqual('Search', self.vocab.step_title)
        self.assertEqual('displayname', self.vocab._orderBy)

    def test_search_empty(self):
        # An empty search will return all active maintained projects.
        results = self.vocab.searchForTerms('')
        self.assertEqual(
            self.num_commercial, len(results),
            "Expected %d results but got %d." % (self.num_proprietary,
                                                 len(results)))

    def test_search_success(self):
        # Search for for active maintained projects success.
        results = self.vocab.searchForTerms('widget')
        self.assertEqual(
            self.num_commercial, len(results),
            "Expected %d results but got %d." % (self.num_proprietary,
                                                 len(results)))
        # Ensure we get only those that match by searching for a single
        # widget, using 't1', a subset of the name 'widget1'.
        results = self.vocab.searchForTerms('t1')
        self.assertEqual(1, len(results),
                         "Expected %d result but got %d." % (1, len(results)))

    def test_search_fail(self):
        # Search for deactivate or non-maintained projects fails.
        results = self.vocab.searchForTerms('norwegian-blue-widget')
        self.assertEqual(0, len(results),
                         "Expected %d results but got %d." %
                         (0, len(results)))

        results = self.vocab.searchForTerms('firefox')
        self.assertEqual(0, len(results),
                         "Expected %d results but got %d." %
                         (0, len(results)))

    def test_toTerm_no_subscription(self):
        # Commercial project terms contain subscription information.
        term = self.vocab.toTerm(self.maintained_project)
        self.assertEqual(self.maintained_project, term.value)
        self.assertEqual('open-widget', term.token)
        self.assertEqual('Open-widget (no subscription)', term.title)

    def test_toTerm_with_subscription(self):
        # Commercial project terms contain subscription information.
        self.factory.makeCommercialSubscription(self.maintained_project)
        cs = self.maintained_project.commercial_subscription
        expiration_date = DateTimeFormatterAPI(cs.date_expires).displaydate()
        term = self.vocab.toTerm(self.maintained_project)
        self.assertEqual(self.maintained_project, term.value)
        self.assertEqual('open-widget', term.token)
        self.assertEqual(
            'Open-widget (expires %s)' % expiration_date, term.title)

    def test_getTermByToken(self):
        # The term for a token in the vocabulary is returned.
        token = self.vocab.getTermByToken('open-widget')
        self.assertEqual(self.maintained_project, token.value)

    def test_getTermByToken_error(self):
        # A LookupError is raised if the token is not in the vocabulary.
        self.assertRaises(
            LookupError, self.vocab.getTermByToken, 'norwegian-blue-widget')

    def test_searchForTerms(self):
        # Seach for terms returns an CountableIterator.
        iterator = self.vocab.searchForTerms('widget')
        self.assertEqual(6, len(iterator))
        terms = [term for term in iterator]
        self.assertEqual('open-widget', terms[0].token)

    def test_iter(self):
        # The vocabulary can be iterated and the order is by displayname.
        displaynames = [p.value.displayname for p in self.vocab]
        self.assertEqual(
            ['Open-widget', 'Widget0', 'Widget1', 'Widget2', 'Widget3',
             'Widget4'],
            displaynames)

    def test_contains_maintainer(self):
        # The vocabulary only contains active projects the user maintains.
        other_project = self.factory.makeProduct()
        self.assertIs(False, other_project in self.vocab)
        self.assertIs(False, self.deactivated_project in self.vocab)
        self.assertIs(True, self.maintained_project in self.vocab)

    def test_contains_commercial_admin(self):
        # The vocabulary contains all active projects for commercial.
        other_project = self.factory.makeProduct()
        with celebrity_logged_in('registry_experts') as expert:
            self.vocab = CommercialProjectsVocabulary(context=expert)
            self.assertIs(True, other_project in self.vocab)
            self.assertIs(False, self.deactivated_project in self.vocab)
            self.assertIs(True, self.maintained_project in self.vocab)
