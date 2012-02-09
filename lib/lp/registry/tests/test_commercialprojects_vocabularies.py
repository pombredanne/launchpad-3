# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the commercial projects vocabularies."""

__metaclass__ = type

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

    def test_search_empty(self):
        """An empty search will return all active maintained projects."""
        results = self.vocab.searchForTerms('')
        self.assertEqual(
            self.num_commercial, len(results),
            "Expected %d results but got %d." % (self.num_proprietary,
                                                 len(results)))

    def test_search_success(self):
        """Search for for active maintained projects success."""
        # All of our commercial projects are named 'widgetn' where n in 0..4.
        # So searching for 'widget' should return the all of the commercial
        # projects.  The open source project 'openwidget' will match the
        # search too, but be filtered out.
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
        """Search for deactivate or non-maintained projects fails."""
        results = self.vocab.searchForTerms('norwegian-blue-widget')
        self.assertEqual(0, len(results),
                         "Expected %d results but got %d." %
                         (0, len(results)))

        results = self.vocab.searchForTerms('firefox')
        self.assertEqual(0, len(results),
                         "Expected %d results but got %d." %
                         (0, len(results)))

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
