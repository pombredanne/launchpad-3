# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test initializing a distroseries using
IDistroSeries.initDerivedDistroSeries."""

__metaclass__ = type

import transaction
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import (
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.registry.interfaces.distroseries import DerivationError
from lp.soyuz.interfaces.distributionjob import (
    IInitializeDistroSeriesJobSource,
    )
from lp.soyuz.scripts.tests.test_initialize_distroseries import (
    InitializationHelperTestCase,
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
            [self.parent.id])

    def test_init_creates_new_job(self):
        self.child.initDerivedDistroSeries(
            self.child.driver, [self.parent.id])
        [job] = list(
            getUtility(IInitializeDistroSeriesJobSource).iterReady())
        self.assertEqual(job.distroseries, self.child)


class TestDeriveDistroSeriesMultipleParents(InitializationHelperTestCase):

    layer = LaunchpadZopelessLayer

    def test_multiple_parents_binary_packages(self):
        # An initialization from many parents (using the package copier)
        # can happen using the same the db user the job will use
        # ('initializedistroseries').
        self.parent1, unused = self.setupParent(
            packages={'p1': '0.1-1'})
        self.parent2, unused = self.setupParent(
            packages={'p2': '2.1'})
        child = self.factory.makeDistroSeries()
        transaction.commit()
        self.layer.switchDbUser('initializedistroseries')

        child = self._fullInitialize(
            [self.parent1, self.parent2], child=child)
        pub_sources = child.main_archive.getPublishedSources(
            distroseries=child)
        binaries = sorted(
            [(p.getBuiltBinaries()[0].binarypackagerelease.sourcepackagename,
              p.getBuiltBinaries()[0].binarypackagerelease.version)
                 for p in pub_sources])

        self.assertEquals(
            [(u'p1', u'0.1-1'), (u'p2', u'2.1')],
            binaries)
