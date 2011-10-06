# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugJobs."""

__metaclass__ = type

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.bugs.interfaces.bugjob import BugJobType
from lp.bugs.model.bugjob import (
    BugJob,
    BugJobDerived,
    )
from lp.testing import TestCaseWithFactory


class BugJobTestCase(TestCaseWithFactory):
    """Test case for basic BugJob gubbins."""

    layer = LaunchpadZopelessLayer

    def test_instantiate(self):
        # BugJob.__init__() instantiates a BugJob instance.
        bug = self.factory.makeBug()

        metadata = ('some', 'arbitrary', 'metadata')
        bug_job = BugJob(
            bug, BugJobType.UPDATE_HEAT, metadata)

        self.assertEqual(bug, bug_job.bug)
        self.assertEqual(BugJobType.UPDATE_HEAT, bug_job.job_type)

        # When we actually access the BugJob's metadata it gets
        # unserialized from JSON, so the representation returned by
        # bug_heat.metadata will be different from what we originally
        # passed in.
        metadata_expected = [u'some', u'arbitrary', u'metadata']
        self.assertEqual(metadata_expected, bug_job.metadata)


class BugJobDerivedTestCase(TestCaseWithFactory):
    """Test case for the BugJobDerived class."""

    layer = LaunchpadZopelessLayer

    def test_create_explodes(self):
        # BugJobDerived.create() will blow up because it needs to be
        # subclassed to work properly.
        bug = self.factory.makeBug()
        self.assertRaises(
            AttributeError, BugJobDerived.create, bug)
