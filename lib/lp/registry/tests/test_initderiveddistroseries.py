# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test initialising a distroseries using
IDistroSeries.initDerivedDistroSeries."""

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
        self.child = self.factory.makeDistroSeries()
        removeSecurityProxy(self.child).driver = self.factory.makePerson()
        login_person(self.child.driver)

    def test_no_permission_to_call(self):
        login(ANONYMOUS)
        self.assertRaises(
            Unauthorized, getattr, self.child, "initDerivedDistroSeries")

    def test_parent_is_not_set(self):
        # When the series already has a parent series, it means that the
        # distroseries has already been derived, and it is forbidden to
        # derive more than once.
        self.factory.makeDistroSeriesParent(
            derived_series=self.child, parent_series=self.parent)
        self.assertRaisesWithContent(
            DerivationError,
            ("DistroSeries {self.child.name} already has parent "
             "series.".format(self=self)),
            self.child.initDerivedDistroSeries, self.child.driver,
            [self.parent])

    def test_init_creates_new_job(self):
        self.child.initDerivedDistroSeries(
            self.child.driver, [self.parent])
        [job] = list(
            getUtility(IInitialiseDistroSeriesJobSource).iterReady())
        self.assertEqual(job.distroseries, self.child)
