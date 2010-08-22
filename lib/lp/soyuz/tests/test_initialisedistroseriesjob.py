# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from canonical.testing import LaunchpadZopelessLayer

from lp.soyuz.model.initialisedistroseriesjob import (
    InitialiseDistroSeriesJob, InitialiseDistroSeriesJobDerived)
from lp.testing import TestCaseWithFactory


class InitialiseDistroSeriesJobTestCase(TestCaseWithFactory):
    """Test case for basic InitialiseDistroSeriesJob gubbins."""

    layer = LaunchpadZopelessLayer

    def test_instantiate(self):
        distroseries = self.factory.makeDistroSeries()

        metadata = ('some', 'arbitrary', 'metadata')
        distroseries_job = InitialiseDistroSeriesJob(
            distroseries, metadata)

        self.assertEqual(distroseries, distroseries_job.distroseries)

        # When we actually access the InitialiseDistroSeriesJob's
        # metadata it gets deserialized from JSON, so the representation
        # returned by distroseries_job.metadata will be different from what
        # we originally passed in.
        metadata_expected = [u'some', u'arbitrary', u'metadata']
        self.assertEqual(metadata_expected, distroseries_job.metadata)

    
class InitialiseDistroSeriesJobDerivedTestCase(TestCaseWithFactory):
    """Test case for the InitialiseDistroSeriesJobDerived class."""

    layer = LaunchpadZopelessLayer
        
    def test_create_explodes(self):
        # InitialiseDistroSeriesJobDerived.create() will blow up because it needs to be
        # subclassed to work properly.
        distroseries = self.factory.makeDistroSeries()
        self.assertRaises(
            AttributeError, InitialiseDistroSeriesJobDerived.create, distroseries)
        
        
def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

