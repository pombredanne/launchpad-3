# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the checkwatches remotebugupdater module."""

__metaclass__ = type

import unittest

import transaction

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.bugs.externalbugtracker.bugzilla import Bugzilla
from lp.bugs.scripts.checkwatches.core import CheckwatchesMaster
from lp.bugs.scripts.checkwatches.remotebugupdater import RemoteBugUpdater
from lp.testing import TestCaseWithFactory


class RemoteBugUpdaterTestCase(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_create(self):
        # CheckwatchesMaster.remote_bug_updater_factory points to the
        # RemoteBugUpdater class, so it can be used to create
        # RemoteBugUpdaters.
        remote_system = Bugzilla('http://example.com')
        remote_bug_id = '42'
        bug_watch_ids = [1, 2]
        unmodified_remote_ids = ['76']

        checkwatches_master = CheckwatchesMaster(transaction)
        updater = checkwatches_master.remote_bug_updater_factory(
            checkwatches_master, remote_system, remote_bug_id,
            bug_watch_ids, unmodified_remote_ids, None)

        self.assertTrue(
            isinstance(updater, RemoteBugUpdater),
            "updater should be an instance of RemoteBugUpdater.")
        self.assertEqual(
            remote_system, updater.external_bugtracker,
            "Unexpected external_bugtracker for RemoteBugUpdater.")
        self.assertEqual(
            remote_bug_id, updater.remote_bug,
            "RemoteBugUpdater's remote_bug should be '%s', was '%s'" %
            (remote_bug_id, updater.remote_bug))
        self.assertEqual(
            bug_watch_ids, updater.bug_watch_ids,
            "RemoteBugUpdater's bug_watch_ids should be '%s', were '%s'" %
            (bug_watch_ids, updater.bug_watch_ids))
        self.assertEqual(
            unmodified_remote_ids, updater.unmodified_remote_ids,
            "RemoteBugUpdater's unmodified_remote_ids should be '%s', "
            "were '%s'" % 
            (unmodified_remote_ids, updater.unmodified_remote_ids))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
