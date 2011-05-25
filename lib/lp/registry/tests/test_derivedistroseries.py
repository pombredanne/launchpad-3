# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test initialising a distroseries using
IDistroSeries.deriveDistroSeries."""

__metaclass__ = type

from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.registry.interfaces.distroseries import DerivationError
from lp.soyuz.interfaces.distributionjob import (
    IInitialiseDistroSeriesJobSource,
    )
from lp.testing import (
    ANONYMOUS,
    login,
    login_person,
    TestCaseWithFactory,
    )


class TestDeriveDistroSeries(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestDeriveDistroSeries, self).setUp()
        self.parent = self.factory.makeDistroSeries()
        removeSecurityProxy(self.parent).driver = self.factory.makePerson()
        self.child = self.factory.makeDistroSeries()
        login_person(self.parent.driver)

    def test_no_permission_to_call(self):
        login(ANONYMOUS)
        self.assertRaises(
            Unauthorized, getattr, self.parent, "deriveDistroSeries")

    def test_no_distroseries_and_no_arguments(self):
        """Test that calling deriveDistroSeries() when the distroseries
        doesn't exist, and not enough arguments are specified that the
        function errors."""
        self.assertRaisesWithContent(
            DerivationError,
            'Display Name needs to be set when creating a distroseries.',
            self.parent.deriveDistroSeries, self.parent.driver,
            'newdistro')

    def test_parent_is_not_set(self):
        # When parent_series is set it means that the distroseries has already
        # been derived, and it is forbidden to derive more than once.
        removeSecurityProxy(self.child).previous_series = self.parent
        self.assertRaisesWithContent(
            DerivationError,
            ("DistroSeries {self.child.name} parent series is "
             "{self.parent.name}, but it must not be set").format(self=self),
            self.parent.deriveDistroSeries, self.parent.driver,
            self.child.name, self.child.distribution)

    def test_create_new_distroseries(self):
        self.parent.deriveDistroSeries(
            self.parent.driver, self.child.name, self.child.distribution)
        [job] = list(
            getUtility(IInitialiseDistroSeriesJobSource).iterReady())
        self.assertEqual(job.distroseries, self.child)

    def test_create_fully_new_distroseries(self):
        self.parent.deriveDistroSeries(
            self.parent.driver, 'deribuntu', displayname='Deribuntu',
            title='The Deribuntu', summary='Deribuntu',
            description='Deribuntu is great', version='11.11')
        [job] = list(
            getUtility(IInitialiseDistroSeriesJobSource).iterReady())
        self.assertEqual(job.distroseries.name, 'deribuntu')

    def test_create_initialises_correct_distribution(self):
        # Make two distroseries with the same name and different
        # distributions to check that the right distroseries is initialised.
        self.factory.makeDistroSeries(name='bar')
        bar = self.factory.makeDistroSeries(name='bar')
        self.parent.deriveDistroSeries(
            self.parent.driver, 'bar', distribution=bar.parent,
            displayname='Bar', title='The Bar', summary='Bar',
            description='Bar is good', version='1.0')
        [job] = list(
            getUtility(IInitialiseDistroSeriesJobSource).iterReady())
        self.assertEqual('bar', job.distroseries.name)
        self.assertEqual(bar.parent.name, job.distribution.name)
