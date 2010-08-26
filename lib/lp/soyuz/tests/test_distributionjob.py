# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from canonical.testing import LaunchpadZopelessLayer

from lp.soyuz.interfaces.distributionjob import (
    DistributionJobType)
from lp.soyuz.model.distributionjob import (
    DistributionJob,
    DistributionJobDerived)
from lp.testing import TestCaseWithFactory


class DistributionJobTestCase(TestCaseWithFactory):
    """Test case for basic DistributionJob usage."""

    layer = LaunchpadZopelessLayer

    def test_instantiate(self):
        distribution = self.factory.makeDistribution()
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution)

        metadata = ('some', 'arbitrary', 'metadata')
        distribution_job = DistributionJob(
            distribution, distroseries,
            DistributionJobType.DO_INITIALISE, metadata)

        self.assertEqual(distribution, distribution_job.distribution)
        self.assertEqual(distroseries, distribution_job.distroseries)
        self.assertEqual(DistributionJobType.DO_INITIALISE,
            distribution_job.job_type)

        # When we actually access the DistributionJob's metadata it gets
        # deserialized from JSON, so the representation returned by
        # foo_job.metadata will be different from what we originally
        # passed in.
        metadata_expected = [u'some', u'arbitrary', u'metadata']
        self.assertEqual(metadata_expected, distribution_job.metadata)

    
class DistributionJobDerivedTestCase(TestCaseWithFactory):
    """Test case for the DistributionJobDerived class."""

    layer = LaunchpadZopelessLayer
        
    def test_create_explodes(self):
        # DistributionJobDerived.create() will blow up because it needs
        # to be subclassed to work properly.
        distribution = self.factory.makeDistribution()
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution)
        self.assertRaises(
            AttributeError, DistributionJobDerived.create, distribution,
            distroseries)
        
        
def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

