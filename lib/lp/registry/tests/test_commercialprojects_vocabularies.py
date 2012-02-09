# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the commercial projects vocabularies."""

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.registry.interfaces.product import (
    IProductSet,
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
        """Create a proprietary projects."""
        # Create 5 proprietary projects.
        self.num_proprietary = 5
        for i in range(self.num_proprietary):
            self.factory.makeProduct(
                name='widget%d' % i, owner=self.owner,
                 licenses=[License.OTHER_PROPRIETARY])
        # Create an open source project.
        self.factory.makeProduct(
            name='open-widget', owner=self.owner,
            licenses=[License.GNU_GPL_V3])
        # Create a deactivated open source project.
        with celebrity_logged_in('admin'):
            self.factory.makeProduct(
                name='norwegian-blue-widget', owner=self.owner,
                licenses=[License.GNU_GPL_V3]).active = False

    def test_emptySearch(self):
        """An empty search should return all commercial projects."""
        results = self.vocab.searchForTerms('')
        self.assertEqual(
            self.num_proprietary, len(results),
            "Expected %d results but got %d." % (self.num_proprietary,
                                                 len(results)))

    def test_SuccessfulSearch(self):
        """Search for a project name that exists."""
        # All of our commercial projects are named 'widgetn' where n in 0..4.
        # So searching for 'widget' should return the all of the commercial
        # projects.  The open source project 'openwidget' will match the
        # search too, but be filtered out.
        results = self.vocab.searchForTerms('widget')
        self.assertEqual(
            self.num_proprietary, len(results),
            "Expected %d results but got %d." % (self.num_proprietary,
                                                 len(results)))
        # Searching on a subset of 'widget' should work also.
        results = self.vocab.searchForTerms('idge')
        self.assertEqual(
            self.num_proprietary, len(results),
            "Expected %d results but got %d." % (self.num_proprietary,
                                                 len(results)))
        # Ensure we get only those that match by searching for a single
        # widget, using 't1', a subset of the name 'widget1'.
        results = self.vocab.searchForTerms('t1')
        self.assertEqual(1, len(results),
                         "Expected %d result but got %d." % (1, len(results)))

    def test_FailedSearch(self):
        """Search for projects that are not commercial projects we own."""
        results = self.vocab.searchForTerms('openwidget')
        self.assertEqual(0, len(results),
                         "Expected %d results but got %d." %
                         (0, len(results)))

        results = self.vocab.searchForTerms('firefox')
        self.assertEqual(0, len(results),
                         "Expected %d results but got %d." %
                         (0, len(results)))

    def test_TransitionedProjectsSearch(self):
        """Search for a project that changes from commercial to open."""
        # The project is commercial so the search succeeds.
        project_name = 'widget1'
        results = self.vocab.searchForTerms(project_name)
        self.assertEqual(1, len(results),
                         "Expected %d result but got %d." % (1, len(results)))

        # Now change the license for the widget.
        widget = getUtility(IProductSet).getByName(project_name)
        naked_widget = removeSecurityProxy(widget)
        naked_widget.licenses = [License.GNU_GPL_V3]

        # The project is no longer commercial so it is not found.
        results = self.vocab.searchForTerms(project_name)
        self.assertEqual(0, len(results),
                         "Expected %d results but got %d." %
                         (0, len(results)))
