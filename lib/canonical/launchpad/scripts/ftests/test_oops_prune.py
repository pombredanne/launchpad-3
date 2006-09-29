# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test the oops-prune.py cronscript and methods in the
   canonical.launchpad.scripts.oops module.
"""

__metaclass__ = type

from datetime import date, timedelta
import os
import shutil
from subprocess import Popen, PIPE, STDOUT
import sys
import tempfile
from textwrap import dedent
import unittest

from canonical.config import config
from canonical.testing import LaunchpadZopelessLayer
from canonical.database.sqlbase import cursor
from canonical.launchpad.scripts.oops import (
        referenced_oops, old_oops_files, unwanted_oops_files
        )
from canonical.launchpad.webapp import errorlog

class TestOopsPrune(unittest.TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.oops_dir = tempfile.mkdtemp()

        # Create some fake OOPS files
        self.today = date.today()
        self.ages_ago = errorlog.epoch + timedelta(days=1)

        for some_date in [self.today, self.ages_ago]:
            date_dir = os.path.join(
                    self.oops_dir, some_date.strftime('%Y-%m-%d')
                    )
            os.mkdir(date_dir)
            for oops_id in ['A666','A1234','A5678']:
                oops_filename = os.path.join(date_dir, '000.%s' % oops_id)
                open(oops_filename, 'w').write('Fnord')

        old_day_count = (self.ages_ago - errorlog.epoch).days + 1

        # Create a reference to one of the old OOPS reports in the DB
        cur = cursor()
        cur.execute("""
            INSERT INTO MessageChunk(message, sequence, content)
            VALUES (1, 99, 'OOPS-%dA666')
            """ % old_day_count)

    def tearDown(self):
        shutil.rmtree(self.oops_dir)

    def path_to_oopsid(self, path):
        '''Extract the OOPS id from a path to an OOPS file'''
        return path.split('.')[-1]

    def test_referenced_oops(self):
        self.failUnlessEqual(
                set(['A666']),
                referenced_oops()
                )

    def test_old_oops_files(self):
        old = set(old_oops_files(self.oops_dir, 90))
        self.failUnlessEqual(len(old), 3)
        # Make sure the paths are valid
        for old_path in old:
            self.failUnless(os.path.exists(old_path))

    def test_unwanted_oops_files(self):
        unwanted = set(unwanted_oops_files(self.oops_dir, 90))
        self.failUnlessEqual(len(unwanted), 2) # One is referenced
        # Make sure that A666 isn't unwanted
        unwanted_ids = set(self.path_to_oopsid(path) for path in unwanted)
        self.failUnlessEqual(
                unwanted_ids,
                set(['A1234', 'A5678'])
                )

    def test_script(self):
        unwanted = unwanted_oops_files(self.oops_dir, 90)
        # Commit so our script can see changes made by the setUp method
        LaunchpadZopelessLayer.commit()
        process = Popen([
                sys.executable,
                os.path.join(config.root, 'cronscripts', 'oops-prune.py'),
                '-q', self.oops_dir,
                ], stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        (out, err) = process.communicate()
        self.failUnlessEqual(out, '')

        # Check out OOPS directory to ensure that there are now only
        # three OOPS reports - 1 in the old directory and 3 in the new one.
        today_dir = os.path.join(
                self.oops_dir, self.today.strftime('%Y-%m-%d')
                )
        found_oops_files = set()
        for dirpath, dirnames, filenames in os.walk(today_dir):
            for filename in filenames:
                found_oops_files.add(self.path_to_oopsid(filename))
        self.failUnlessEqual(
                found_oops_files,
                set(['A666', 'A1234', 'A5678'])
                )

        old_dir = os.path.join(
                self.oops_dir, self.ages_ago.strftime('%Y-%m-%d')
                )
        found_oops_files = set()
        for dirpath, dirnames, filenames in os.walk(old_dir):
            for filename in filenames:
                found_oops_files.add(self.path_to_oopsid(filename))
        self.failUnlessEqual(
                found_oops_files,
                set(['A666'])
                )


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

