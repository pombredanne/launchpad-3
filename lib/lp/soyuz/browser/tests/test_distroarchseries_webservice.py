# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.security.management import endInteraction

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    launchpadlib_for,
    ws_object,
    TestCaseWithFactory,
    )


class TestDistroArchSeriesWebservice(TestCaseWithFactory):
    """Unit Tests for 'DistroArchSeries' Webservice.
    """
    layer = DatabaseFunctionalLayer

    def _makeDistroArchSeries(self):
        """Create a `DistroSeries` object, that is prefilled with 1
        architecture for testing purposes.

        :return: a `DistroSeries` object.
        """
        distro = self.factory.makeDistribution()
        distroseries = self.factory.makeDistroSeries(
            distribution=distro)
        self.factory.makeDistroArchSeries(
            distroseries=distroseries)

        return distroseries

    def test_distroseries_architectures_anonymous(self):
        """Test anonymous DistroArchSeries API Access."""
        distroseries = self._makeDistroArchSeries()
        endInteraction()
        launchpad = launchpadlib_for('test', person=None, version='devel')
        ws_distroseries = ws_object(launchpad, distroseries)
        #Note, we test the length of architectures.entries, not
        #architectures due to the removal of the entries by lazr
        self.assertEqual(1, len(ws_distroseries.architectures.entries))

    def test_distroseries_architectures_authenticated(self):
        """Test authenticated DistroArchSeries API Access."""
        distroseries = self._makeDistroArchSeries()
        #Create a user to use the authenticated API
        accessor = self.factory.makePerson()
        launchpad = launchpadlib_for('test', accessor.name, version='devel')
        ws_distroseries = ws_object(launchpad, distroseries)
        #See note above regarding testing of length of .entries
        self.assertEqual(1, len(ws_distroseries.architectures.entries))
