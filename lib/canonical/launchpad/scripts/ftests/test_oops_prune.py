# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test the oops-prune.py cronscript and methods in the
   canonical.launchpad.scripts.oops module.
"""

__metaclass__ = type

from datetime import datetime, timedelta
import os
import re
import shutil
from subprocess import Popen, PIPE, STDOUT
import sys
import tempfile
import unittest

from pytz import UTC

from canonical.config import config
from canonical.testing import LaunchpadZopelessLayer
from canonical.database.sqlbase import cursor
from canonical.launchpad.scripts.oops import (
        referenced_oops, old_oops_files, unwanted_oops_files,
        path_to_oopsid, prune_empty_oops_directories
        )
from canonical.launchpad.webapp import errorlog

class TestOopsPrune(unittest.TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        # The dots in the directory name are here because we had a bug
        # where this situation would break due to using split('.') on the
        # whole path rather than the path's basename.
        self.oops_dir = tempfile.mkdtemp('.directory.with.dots')

        # Create some fake OOPS files
        self.today = datetime.now(tz=UTC)
        self.ages_ago = errorlog.epoch + timedelta(days=1)
        self.awhile_ago = self.ages_ago + timedelta(days=1)

        for some_date in [self.today, self.ages_ago, self.awhile_ago]:
            date_dir = os.path.join(
                    self.oops_dir, some_date.strftime('%Y-%m-%d')
                    )
            os.mkdir(date_dir)
            # Note - one of these is lowercase to demonstrate case handling
            for oops_id in ['A666', 'A1234.gz', 'A5678.bz2', 'a666']:
                oops_filename = os.path.join(date_dir, '000.%s' % oops_id)
                open(oops_filename, 'w').write('Fnord')

        # Create a reference to one of the old OOPS reports in the DB
        self.referenced_oops_code = '2A666'
        cur = cursor()
        cur.execute("""
            INSERT INTO MessageChunk(message, sequence, content)
            VALUES (1, 99, 'OOPS-%s')
            """ % self.referenced_oops_code)

    def tearDown(self):
        shutil.rmtree(self.oops_dir)

    def test_referenced_oops(self):
        self.failUnlessEqual(
                set([self.referenced_oops_code]),
                referenced_oops()
                )

        # We also check in other places besides MessageChunk for oops ids
        cur = cursor()
        cur.execute("UPDATE Message SET subject='OOPS-1MessageSubject666'")
        cur.execute("""
            UPDATE Bug SET
                title='OOPS-1BugTitle666',
                description='OOPS-1BugDescription666'
            """)
        cur.execute("""
            UPDATE BugTask
                SET statusexplanation='foo OOPS1BugTaskStatusExplanation666'
            """)
        cur.execute("""
            UPDATE Question SET
                title='OOPS - 1TicketTitle666 bar',
                description='http://foo.com OOPS-1TicketDescription666',
                whiteboard='OOPS-1TicketWhiteboard666'
                WHERE id=1
            """)
        # Add a question entry with a NULL whiteboard to ensure the SQL query
        # copes.
        cur.execute("""
            UPDATE Question SET
                title='OOPS - 1TicketTitle666 bar',
                description='http://foo.com OOPS-1TicketDescription666',
                whiteboard=NULL
                WHERE id=2
            """)
        self.failUnlessEqual(
                set([
                    self.referenced_oops_code,
                    '1MESSAGESUBJECT666',
                    '1BUGTITLE666',
                    '1BUGDESCRIPTION666',
                    '1BUGTASKSTATUSEXPLANATION666',
                    '1TICKETTITLE666',
                    '1TICKETDESCRIPTION666',
                    '1TICKETWHITEBOARD666',
                    ]),
                referenced_oops()
                )

    def test_old_oops_files(self):
        old = set(old_oops_files(self.oops_dir, 90))
        self.failUnlessEqual(len(old), 8)
        # Make sure the paths are valid
        for old_path in old:
            self.failUnless(os.path.exists(old_path))
            self.failUnless(
                    '2006-01' in old_path, '%s not in old area' % old_path
                    )

    def test_unwanted_oops_files(self):
        unwanted = set(unwanted_oops_files(self.oops_dir, 90))
        # Make sure that 2A666 and 2a666 are wanted.
        unwanted_ids = set(path_to_oopsid(path) for path in unwanted)
        self.failUnlessEqual(
            unwanted_ids,
            set(['2A1234', '2A5678', '3A666', '3a666', '3A1234', '3A5678'])
            )
        # Make sure the paths are valid
        for unwanted_path in unwanted:
            self.failUnless(os.path.exists(unwanted_path))
            self.failUnless(
                    '2006-01' in unwanted_path,
                    'New OOPS %s unwanted' % unwanted_path
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
                found_oops_files.add(
                        path_to_oopsid(os.path.join(dirpath,filename))
                        )
        today_day_count = (self.today - errorlog.epoch).days + 1
        self.failUnlessEqual(
                found_oops_files,
                set([
                    '%dA666' % today_day_count,
                    '%da666' % today_day_count,
                    '%dA1234' % today_day_count,
                    '%dA5678' % today_day_count,
                    ])
                )

        old_dir = os.path.join(
                self.oops_dir, self.ages_ago.strftime('%Y-%m-%d')
                )
        found_oops_files = set()
        for dirpath, dirnames, filenames in os.walk(old_dir):
            for filename in filenames:
                found_oops_files.add(
                        path_to_oopsid(os.path.join(dirpath, filename))
                        )
        # Note that we err on the side of caution when we find files
        # differing by case.
        self.failUnlessEqual(
                found_oops_files,
                set(['2A666', '2a666'])
                )

        # The directory containing only old, unreferenced OOPS files should
        # have been removed.
        self.failIf(
                os.path.isdir(os.path.join(self.oops_dir, '2006-01-03')),
                'Script failed to remove 2006-01-03 directory'
                )


    def test_script_dryrun(self):
        unwanted = unwanted_oops_files(self.oops_dir, 90)
        # Commit so our script can see changes made by the setUp method
        LaunchpadZopelessLayer.commit()

        # Count how many OOPS reports there currently are
        orig_count = 0
        for dirpath, dirnames, filenames in os.walk(self.oops_dir):
            for filename in filenames:
                if re.search(
                    r'^\d+\.\d+[a-zA-Z]\d+(?:\.gz|\.bz2)?$', filename):
                    orig_count += 1

        # Run the script, which should make no changes with the --dry-run
        # option.
        process = Popen([
                sys.executable,
                os.path.join(config.root, 'cronscripts', 'oops-prune.py'),
                '-q', '--dry-run', self.oops_dir,
                ], stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        (out, err) = process.communicate()
        self.failUnlessEqual(out, '')

        # Check out OOPS directory to ensure that no OOPS reports have
        # been removed.
        new_count = 0
        for dirpath, dirnames, filenames in os.walk(self.oops_dir):
            for filename in filenames:
                if re.search(
                    r'^\d+\.\d+[a-zA-Z]\d+(?:\.gz|\.bz2)?$', filename):
                    new_count += 1

        self.failUnlessEqual(orig_count, new_count)

    def test_script_default_error_dir(self):
        # Verify that the script runs without the error_dir argument.
        default_error_dir = config.error_reports.error_dir
        unwanted = unwanted_oops_files(default_error_dir, 90)
        # Commit so our script can see changes made by the setUp method.
        LaunchpadZopelessLayer.commit()
        process = Popen([
            sys.executable,
            os.path.join(config.root, 'cronscripts', 'oops-prune.py'), '-q'],
            stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        (out, err) = process.communicate()
        self.failUnlessEqual(out, '')

    def test_prune_empty_oops_directories(self):
        # And a directory empty of OOPS reports
        os.mkdir(os.path.join(self.oops_dir, '2038-12-01'))
        os.mkdir(os.path.join(self.oops_dir, '2001-12-01'))

        # And a directory empty of OOPS reports, but with some rubbish
        os.mkdir(os.path.join(self.oops_dir, '2001-12-02'))
        open(
                os.path.join( self.oops_dir, '2001-12-02', 'foo'), 'w'
                ).write('foo')

        prune_empty_oops_directories(self.oops_dir)

        # Most directories should still be there
        for date in ['2006-01-02', '2006-01-03', '2001-12-02']:
            self.failUnless(
                os.path.isdir(os.path.join(self.oops_dir, date))
                )

        # But the empty ones should be gone
        for date in ['2038-12-01', '2001-12-01']:
            self.failIf(
                os.path.isdir(os.path.join(self.oops_dir, date))
                )


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

