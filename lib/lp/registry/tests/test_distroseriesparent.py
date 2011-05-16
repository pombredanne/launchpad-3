# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for DistroSeriesParent model class."""

__metaclass__ = type

from testtools.matchers import (
    Equals,
    MatchesStructure,
    )
from zope.component import getUtility
from zope.interface.verify import verifyObject
from zope.security.interfaces import Unauthorized

from canonical.launchpad.ftests import login
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    ZopelessDatabaseLayer,
    )
from lp.registry.interfaces.distroseriesparent import (
    IDistroSeriesParent,
    IDistroSeriesParentSet,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.sampledata import LAUNCHPAD_ADMIN
from lp.soyuz.interfaces.component import IComponentSet


class TestDistroSeriesParent(TestCaseWithFactory):
    """Test the `DistroSeriesParent` model."""
    layer = ZopelessDatabaseLayer

    def test_verify_interface(self):
        # Test the interface for the model.
        dsp = self.factory.makeDistroSeriesParent()
        verified = verifyObject(IDistroSeriesParent, dsp)
        self.assertTrue(verified)

    def test_properties(self):
        # Test the model properties.
        parent_series = self.factory.makeDistroSeries()
        derived_series = self.factory.makeDistroSeries()
        dsp = self.factory.makeDistroSeriesParent(
            derived_series=derived_series,
            parent_series=parent_series,
            initialized=True
            )

        self.assertThat(
            dsp,
            MatchesStructure(
                derived_series=Equals(derived_series),
                parent_series=Equals(parent_series),
                initialized=Equals(True),
                is_overlay=Equals(False),
                component=Equals(None),
                pocket=Equals(None),
                ))

    def test_properties_overlay(self):
        # Test the model properties if the DSP represents an overlay.
        parent_series = self.factory.makeDistroSeries()
        derived_series = self.factory.makeDistroSeries()
        main_component = getUtility(IComponentSet).ensure('main')
        dsp = self.factory.makeDistroSeriesParent(
            derived_series=derived_series,
            parent_series=parent_series,
            initialized=True,
            is_overlay=True,
            component=main_component,
            pocket=PackagePublishingPocket.SECURITY,
            )

        self.assertThat(
            dsp,
            MatchesStructure(
                derived_series=Equals(derived_series),
                parent_series=Equals(parent_series),
                initialized=Equals(True),
                is_overlay=Equals(True),
                component=Equals(main_component),
                pocket=Equals(PackagePublishingPocket.SECURITY),
                ))

    def test_getByDerivedSeries(self):
        parent_series = self.factory.makeDistroSeries()
        derived_series = self.factory.makeDistroSeries()
        self.factory.makeDistroSeriesParent(
            derived_series, parent_series)
        results = getUtility(IDistroSeriesParentSet).getByDerivedSeries(
            derived_series)
        self.assertEqual(1, results.count())
        self.assertEqual(parent_series, results[0].parent_series)

        # Making a second parent should add it to the results.
        self.factory.makeDistroSeriesParent(
            derived_series, self.factory.makeDistroSeries())
        results = getUtility(IDistroSeriesParentSet).getByDerivedSeries(
            derived_series)
        self.assertEqual(2, results.count())

    def test_getByParentSeries(self):
        parent_series = self.factory.makeDistroSeries()
        derived_series = self.factory.makeDistroSeries()
        self.factory.makeDistroSeriesParent(
            derived_series, parent_series)
        results = getUtility(IDistroSeriesParentSet).getByParentSeries(
            parent_series)
        self.assertEqual(1, results.count())
        self.assertEqual(derived_series, results[0].derived_series)

        # Making a second child should add it to the results.
        self.factory.makeDistroSeriesParent(
            self.factory.makeDistroSeries(), parent_series)
        results = getUtility(IDistroSeriesParentSet).getByParentSeries(
            parent_series)
        self.assertEqual(2, results.count())


class TestDistroSeriesParentSecurity(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_random_person_is_unauthorized(self):
        dsp = self.factory.makeDistroSeriesParent()
        person = self.factory.makePerson()
        with person_logged_in(person):
            self.assertRaises(
                Unauthorized,
                setattr, dsp, "derived_series", dsp.parent_series)

    def assertCanEdit(self, dsp):
        dsp.initialized = False
        self.assertEquals(False, dsp.initialized)

    def test_distroseries_drivers_can_edit(self):
        # Test that distroseries drivers can edit the data.
        dsp = self.factory.makeDistroSeriesParent()
        person = self.factory.makePerson()
        login(LAUNCHPAD_ADMIN)
        dsp.derived_series.driver = person
        with person_logged_in(person):
            self.assertCanEdit(dsp)

    def test_admins_can_edit(self):
        dsp = self.factory.makeDistroSeriesParent()
        login(LAUNCHPAD_ADMIN)
        self.assertCanEdit(dsp)

    def test_distro_owners_can_edit(self):
        dsp = self.factory.makeDistroSeriesParent()
        person = self.factory.makePerson()
        login(LAUNCHPAD_ADMIN)
        dsp.derived_series.distribution.owner = person
        with person_logged_in(person):
            self.assertCanEdit(dsp)


class TestOverlayTree(TestCaseWithFactory):
    """Test the overlay tree."""

    layer = DatabaseFunctionalLayer

    def test_getFlattenedOverlayTree(self):
        #        /-o- parent11 -o- parent12 --- parent13
        # series
        #        \-o- parent21 -o- parent22
        #         \--- parent31
        #          \-o- parent41
        # -o-: overlay
        # ---: not overlay
        distroseries = self.factory.makeDistroSeries()
        parent11 = self.factory.makeDistroSeries()
        parent12 = self.factory.makeDistroSeries()
        parent21 = self.factory.makeDistroSeries()
        main_component = getUtility(IComponentSet).ensure('main')
        # series -> parent11
        s_p11 = self.factory.makeDistroSeriesParent(
            derived_series=distroseries, parent_series=parent11,
            initialized=True, is_overlay=True,
            pocket=PackagePublishingPocket.RELEASE, component=main_component)
        # parent11 -> parent12
        p11_p12 = self.factory.makeDistroSeriesParent(
            derived_series=parent11, parent_series=parent12,
            initialized=True, is_overlay=True,
            pocket=PackagePublishingPocket.RELEASE, component=main_component)
        # parent12 -> parent13
        self.factory.makeDistroSeriesParent(derived_series=parent12,
            initialized=True, is_overlay=False)
        # series -> parent2
        s_p2 = self.factory.makeDistroSeriesParent(
            derived_series=distroseries, parent_series=parent21,
            initialized=True, is_overlay=True,
            pocket=PackagePublishingPocket.RELEASE, component=main_component)
        # parent21 -> parent22
        p21_p22 = self.factory.makeDistroSeriesParent(
            derived_series=parent21, initialized=True, is_overlay=True,
            pocket=PackagePublishingPocket.RELEASE, component=main_component)
        # series -> parent31
        self.factory.makeDistroSeriesParent(derived_series=distroseries,
            initialized=True, is_overlay=False)
        # series -> parent41
        s_p4 = self.factory.makeDistroSeriesParent(
            derived_series=distroseries, initialized=True, is_overlay=True,
            pocket=PackagePublishingPocket.RELEASE, component=main_component)
        overlays = getUtility(
            IDistroSeriesParentSet).getFlattenedOverlayTree(distroseries)

        self.assertContentEqual(
            [s_p11, p11_p12, s_p2, p21_p22, s_p4], overlays)

    def test_getFlattenedOverlayTree_empty(self):
        distroseries = self.factory.makeDistroSeries()
        self.factory.makeDistroSeriesParent(derived_series=distroseries,
            initialized=True, is_overlay=False)
        overlays = getUtility(
            IDistroSeriesParentSet).getFlattenedOverlayTree(distroseries)

        self.assertTrue(overlays.is_empty())
