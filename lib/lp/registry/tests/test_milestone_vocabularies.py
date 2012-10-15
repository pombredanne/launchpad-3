# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the milestone vocabularies."""

__metaclass__ = type

from unittest import TestCase

from zope.component import getUtility

from lp.blueprints.interfaces.specification import ISpecificationSet
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProductSet
from lp.registry.interfaces.projectgroup import IProjectGroupSet
from lp.registry.vocabularies import MilestoneVocabulary
from lp.testing import (
    login,
    logout,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestMilestoneVocabulary(TestCase):
    """Test that the MilestoneVocabulary behaves as expected."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        login('test@canonical.com')

    def tearDown(self):
        logout()

    def testProductMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a product."""
        firefox = getUtility(IProductSet).getByName('firefox')
        vocabulary = MilestoneVocabulary(firefox)
        self.assertEqual(
            [term.title for term in vocabulary], [u'Mozilla Firefox 1.0'])

    def testProductSeriesMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a product series."""
        firefox = getUtility(IProductSet).getByName('firefox')
        trunk = firefox.getSeries('trunk')
        vocabulary = MilestoneVocabulary(trunk)
        self.assertEqual(
            [term.title for term in vocabulary], [u'Mozilla Firefox 1.0'])

    def testProjectMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a project."""
        mozilla = getUtility(IProjectGroupSet).getByName('mozilla')
        vocabulary = MilestoneVocabulary(mozilla)
        self.assertEqual(
            [term.title for term in vocabulary], [u'Mozilla Firefox 1.0'])

    def testDistributionMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a distribution."""
        debian = getUtility(IDistributionSet).getByName('debian')
        vocabulary = MilestoneVocabulary(debian)
        self.assertEqual(
            [term.title for term in vocabulary],
            [u'Debian 3.1', u'Debian 3.1-rc1'])

    def testDistroseriesMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a distroseries."""
        debian = getUtility(IDistributionSet).getByName('debian')
        woody = debian.getSeries('woody')
        vocabulary = MilestoneVocabulary(woody)
        self.assertEqual(
            [term.title for term in vocabulary],
            [u'Debian 3.1', u'Debian 3.1-rc1'])

    def testSpecificationMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a specification."""
        spec = getUtility(ISpecificationSet).get(1)
        firefox = getUtility(IProductSet).getByName('firefox')
        self.assertEqual(spec.target, firefox)
        vocabulary = MilestoneVocabulary(spec)
        self.assertEqual(
            [term.title for term in vocabulary], [u'Mozilla Firefox 1.0'])

    def testPersonMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a person."""
        sample_person = getUtility(IPersonSet).getByEmail(
            'test@canonical.com')
        vocabulary = MilestoneVocabulary(sample_person)
        # A person is not a milestone target; the vocabulary consists
        # in such a case of all known visible milestones.
        self.assertEqual(
            [term.title for term in vocabulary],
            [u'Debian 3.1', u'Debian 3.1-rc1', u'Mozilla Firefox 1.0'])
