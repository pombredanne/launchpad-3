# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the unique log naming facility."""

__metaclass__ = type

import datetime
import os
import shutil
import stat
import tempfile
import unittest

import pytz
import testtools

from lp.services.log.uniquefileallocator import UniqueFileAllocator


UTC = pytz.timezone('UTC')


class TestUniqueFileAllocator(testtools.TestCase):

    def setUp(self):
        super(TestUniqueFileAllocator, self).setUp()
        tempdir = tempfile.mkdtemp()
        self._tempdir = tempdir
        self.addCleanup(shutil.rmtree, tempdir, ignore_errors=True)

    def test_setToken(self):
        namer = UniqueFileAllocator("/any-old/path/", 'OOPS', 'T')
        self.assertEqual('T', namer.get_log_infix())

        # Some scripts will append a string token to the prefix.
        namer.setToken('CW')
        self.assertEqual('TCW', namer.get_log_infix())

        # Some scripts run multiple processes and append a string number
        # to the prefix.
        namer.setToken('1')
        self.assertEqual('T1', namer.get_log_infix())

    def assertUniqueFileAllocator(self, namer, now, expected_id,
        expected_last_id, expected_suffix, expected_lastdir):
        logid, filename = namer.newId(now)
        self.assertEqual(logid, expected_id)
        self.assertEqual(filename,
            os.path.join(namer._output_root, expected_suffix))
        self.assertEqual(namer._last_serial, expected_last_id)
        self.assertEqual(namer._last_output_dir,
            os.path.join(namer._output_root, expected_lastdir))

    def test_newId(self):
        # TODO: This should return an id, fileobj instead of a file name, to
        # reduce races with threads that are slow to use what they asked for,
        # when combined with configuration changes causing disk scans. That
        # would also permit using a completely stubbed out file system,
        # reducing IO in tests that use UniqueFileAllocator (such as all the
        # pagetests in Launchpad. At that point an interface to obtain a
        # factory of UniqueFileAllocator's would be useful to parameterise the
        # entire test suite.
        namer = UniqueFileAllocator(self._tempdir, 'OOPS', 'T')
        # first name of the day
        self.assertUniqueFileAllocator(namer,
            datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC),
            'OOPS-91T1', 1, '2006-04-01/01800.T1', '2006-04-01')
        # second name of the day
        self.assertUniqueFileAllocator(namer,
            datetime.datetime(2006, 04, 01, 12, 00, 00, tzinfo=UTC),
            'OOPS-91T2', 2, '2006-04-01/43200.T2', '2006-04-01')

        # first name of the following day sets a new dir and the id starts
        # over.
        self.assertUniqueFileAllocator(namer,
            datetime.datetime(2006, 04, 02, 00, 30, 00, tzinfo=UTC),
            'OOPS-92T1', 1, '2006-04-02/01800.T1', '2006-04-02')

        # Setting a token inserts the token into the filename.
        namer.setToken('YYY')
        logid, filename = namer.newId(
            datetime.datetime(2006, 04, 02, 00, 30, 00, tzinfo=UTC))
        self.assertEqual(logid, 'OOPS-92TYYY2')

        # Setting a type controls the log id:
        namer.setToken('')
        namer._log_type = "PROFILE"
        logid, filename = namer.newId(
            datetime.datetime(2006, 04, 02, 00, 30, 00, tzinfo=UTC))
        self.assertEqual(logid, 'PROFILE-92T3')

        # Native timestamps are not permitted - UTC only.
        now = datetime.datetime(2006, 04, 02, 00, 30, 00)
        self.assertRaises(ValueError, namer.newId, now)

    def test_changeErrorDir(self):
        """Test changing the log output dir."""
        namer = UniqueFileAllocator(self._tempdir, 'OOPS', 'T')

        # First an id in the original error directory.
        self.assertUniqueFileAllocator(namer,
            datetime.datetime(2006, 04, 01, 00, 30, 00, tzinfo=UTC),
            'OOPS-91T1', 1, '2006-04-01/01800.T1', '2006-04-01')

        # UniqueFileAllocator uses the _output_root attribute to get the
        # current output directory.
        new_output_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, new_output_dir, ignore_errors=True)
        namer._output_root = new_output_dir

        # Now an id on the same day, in the new directory.
        now = datetime.datetime(2006, 04, 01, 12, 00, 00, tzinfo=UTC)
        log_id, filename = namer.newId(now)

        # Since it's a new directory, with no previous logs, the id is 1
        # again, rather than 2.
        self.assertEqual(log_id, 'OOPS-91T1')
        self.assertEqual(namer._last_serial, 1)
        self.assertEqual(namer._last_output_dir,
            os.path.join(new_output_dir, '2006-04-01'))

    def test_findHighestSerial(self):
        namer = UniqueFileAllocator(self._tempdir, "OOPS", "T")
        # Creates the dir using now as the timestamp.
        output_dir = namer.output_dir()
        # write some files, in non-serial order.
        open(os.path.join(output_dir, '12343.T1'), 'w').close()
        open(os.path.join(output_dir, '12342.T2'), 'w').close()
        open(os.path.join(output_dir, '12345.T3'), 'w').close()
        open(os.path.join(output_dir, '1234567.T0010'), 'w').close()
        open(os.path.join(output_dir, '12346.A42'), 'w').close()
        open(os.path.join(output_dir, '12346.B100'), 'w').close()
        # The namer should figure out the right highest serial.
        self.assertEqual(namer._findHighestSerial(output_dir), 10)

    def test_output_dir_permission(self):
        # Set up default dir creation mode to rwx------.
        umask_permission = stat.S_IRWXG | stat.S_IRWXO
        old_umask = os.umask(umask_permission)
        namer = UniqueFileAllocator(self._tempdir, "OOPS", "T")
        output_dir = namer.output_dir()
        st = os.stat(output_dir)
        # Permission we want here is: rwxr-xr-x
        wanted_permission = (
            stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH |
            stat.S_IXOTH)
        # Get only the permission bits for this directory.
        dir_permission = stat.S_IMODE(st.st_mode)
        self.assertEqual(dir_permission, wanted_permission)
        # Restore the umask to the original value.
        ignored = os.umask(old_umask)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
