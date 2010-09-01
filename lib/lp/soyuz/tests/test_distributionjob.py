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
        distroseries = self.factory.makeDistroSeries()

        metadata = ('some', 'arbitrary', 'metadata')
        distribution_job = DistributionJob(
            distroseries.distribution, distroseries,
            DistributionJobType.INITIALISE_SERIES, metadata)

        self.assertEqual(
            distroseries.distribution, distribution_job.distribution)
        self.assertEqual(distroseries, distribution_job.distroseries)
        self.assertEqual(DistributionJobType.INITIALISE_SERIES,
            distribution_job.job_type)

        # When we actually access the DistributionJob's metadata it gets
        # deserialized from JSON, so the representation returned by
        # foo_job.metadata will be different from what we originally
        # passed in.
        metadata_expected = [u'some', u'arbitrary', u'metadata']
        self.assertEqual(metadata_expected, distribution_job.metadata)
