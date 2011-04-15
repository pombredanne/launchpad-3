# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for DistroSeriesParent model class."""

__metaclass__ = type

from testtools.matchers import (
    Equals,
    MatchesStructure,
    )


from storm.store import Store
from storm.exceptions import IntegrityError
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
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.sampledata import LAUNCHPAD_ADMIN


class TestDistroSeriesParent(TestCaseWithFactory):
    """Test the `DistroSeriesParent` model."""
    layer = ZopelessDatabaseLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        #self.distribution = self.factory.makeDistribution(name='conftest')

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
                initialized=Equals(True)
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
        dsp = self.factory.makeDistroSeriesParent(
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

    def setUp(self):
        super(TestDistroSeriesParentSecurity, self).setUp()
        self.dsp_set = getUtility(IDistroSeriesParentSet)
        self.parent_series = self.factory.makeDistroSeries()
        self.derived_series = self.factory.makeDistroSeries()
        self.person = self.factory.makePerson()

    def test_random_person_is_unauthorized(self):
        with person_logged_in(self.person):
            self.assertRaises(
                Unauthorized,
                self.dsp_set.new, self.derived_series, self.derived_series,
                False)

    def test_distro_drivers_edit(self):
        # Test that distro drivers can edit the data.
        login(LAUNCHPAD_ADMIN)
        self.derived_series.distribution.driver = self.person
        with person_logged_in(self.person):
            dsp = self.dsp_set.new(
                self.derived_series, self.parent_series, False)
            self.assertThat(
                dsp,
                MatchesStructure(
                    derived_series=Equals(self.derived_series),
                    parent_series=Equals(self.parent_series),
                    initialized=Equals(False)
                    ))

    #def test_    
