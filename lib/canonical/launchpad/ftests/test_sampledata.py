# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type


import os
import subprocess
import unittest

from canonical.testing import LaunchpadLayer


class SampleDataTestCase(unittest.TestCase):
    """Sampledata sanity checks."""
    layer = LaunchpadLayer

    def test_new_sample_data(self):
        """Test that new sampe data is the same as the current sample data.

        Some schema changes implcitly alter launchpad sample data.
        For example, adding a column in a schema patch also adds that column
        to sampledata/newsampledata.sql when make newsampledata is next run.
        A developer should only see his changes in newsampledata, not someone
        eles'. newsampledata.sql must always be the same as current.sql when
        the branch is merged.
        """
        sampledata_dir = 'database/sampledata'
        current_sql = os.path.join(sampledata_dir, 'current.sql')
        newsampledata_sql = os.path.join(sampledata_dir, 'newsampledata.sql')
        # Call `make newsampledata` as we expect a developer to do it.
        process = subprocess.Popen(
            ['make', 'newsampledata'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        (out, err) = process.communicate()
        self.failUnlessEqual(
                process.returncode, 0, 'newsampledata.sql was not created.')
        # Verify that there are no differences between current.sql and
        # newsampledata.py
        process = subprocess.Popen(
            ['diff', '-q', current_sql, newsampledata_sql],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        (out, err) = process.communicate()
        self.failUnlessEqual(
                out, '', 'newsampledata.sql differs from current.sql.')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
