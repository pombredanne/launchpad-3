# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the milestone vocabularies."""

__metaclass__ = type

from unittest import TestCase

from zope.component import getUtility

from canonical.launchpad.ftests import (
    login,
    logout,
    )
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.blueprints.interfaces.specification import ISpecificationSet
from lp.bugs.interfaces.bugtask import IBugTaskSet
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProductSet
from lp.registry.interfaces.projectgroup import IProjectGroupSet
from lp.registry.vocabularies import MilestoneVocabulary
from lp.testing.factory import LaunchpadObjectFactory


class TestMilestoneVocabulary(TestCase):
    """Test that the BranchVocabulary behaves as expected."""
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

    def testUpstreamBugTaskMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a upstraem bugtask."""
        bugtask = getUtility(IBugTaskSet).get(2)
        firefox = getUtility(IProductSet).getByName('firefox')
        self.assertEqual(bugtask.product, firefox)
        vocabulary = MilestoneVocabulary(bugtask)
        self.assertEqual(
            [term.title for term in vocabulary], [u'Mozilla Firefox 1.0'])

    def testDistributionBugTaskMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a distribution."""
        bugtask = getUtility(IBugTaskSet).get(4)
        debian = getUtility(IDistributionSet).getByName('debian')
        self.assertEqual(bugtask.distribution, debian)
        vocabulary = MilestoneVocabulary(bugtask)
        self.assertEqual(
            [term.title for term in vocabulary],
            [u'Debian 3.1', u'Debian 3.1-rc1'])

    def testDistroseriesBugTaskMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a distroseries."""
        bugtask = getUtility(IBugTaskSet).get(18)
        debian = getUtility(IDistributionSet).getByName('debian')
        woody = debian.getSeries('woody')
        self.assertEqual(bugtask.distroseries, woody)
        vocabulary = MilestoneVocabulary(bugtask)
        self.assertEqual(
            [term.title for term in vocabulary],
            [u'Debian 3.1', u'Debian 3.1-rc1'])

    def testProductseriesBugTaskMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a productseries."""
        bugtask = getUtility(IBugTaskSet).get(29)
        firefox = getUtility(IProductSet).getByName('firefox')
        series_1_0 = firefox.getSeries('1.0')
        self.assertEqual(bugtask.productseries, series_1_0)
        vocabulary = MilestoneVocabulary(bugtask)
        self.assertEqual(
            [term.title for term in vocabulary], [u'Mozilla Firefox 1.0'])

    def testDistributionsourcepackageBugTaskMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a productseries."""
        factory = LaunchpadObjectFactory()
        debian = getUtility(IDistributionSet).getByName('debian')
        distro_sourcepackage = factory.makeDistributionSourcePackage(
            distribution=debian)
        factory.makeSourcePackagePublishingHistory(
            distroseries=debian.currentseries,
            sourcepackagename=distro_sourcepackage.sourcepackagename)
        bugtask = factory.makeBugTask(target=distro_sourcepackage)
        vocabulary = MilestoneVocabulary(bugtask)
        self.assertEqual(
            [term.title for term in vocabulary],
            [u'Debian 3.1', u'Debian 3.1-rc1'])

    def testSourcepackageBugTaskMilestoneVocabulary(self):
        """Test of MilestoneVocabulary for a productseries."""
        factory = LaunchpadObjectFactory()
        debian = getUtility(IDistributionSet).getByName('debian')
        woody = debian.getSeries('woody')
        sourcepackage = factory.makeSourcePackage(
            distroseries=woody)
        bugtask = factory.makeBugTask(target=sourcepackage)
        vocabulary = MilestoneVocabulary(bugtask)
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
