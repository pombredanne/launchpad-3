# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test the database garbage collector."""

__metaclass__ = type
__all__ = []

from datetime import datetime, timedelta
import time
import unittest

from pytz import UTC
from storm.locals import Min
import transaction

from canonical.launchpad.database.codeimportresult import CodeImportResult
from canonical.launchpad.database.oauth import OAuthNonce
from canonical.launchpad.database.openidconsumer import OpenIDConsumerNonce
from canonical.launchpad.interfaces import IMasterStore
from canonical.launchpad.interfaces.codeimportresult import (
    CodeImportResultStatus)
from canonical.launchpad.testing import TestCase
from canonical.launchpad.scripts.garbo import (
    DailyDatabaseGarbageCollector, HourlyDatabaseGarbageCollector)
from canonical.launchpad.scripts.tests import run_script
from canonical.launchpad.scripts.logger import QuietFakeLogger
from canonical.testing.layers import (
    DatabaseLayer, LaunchpadScriptLayer, LaunchpadZopelessLayer)


class TestGarboScript(TestCase):
    layer = LaunchpadScriptLayer

    def test_daily_script(self):
        """Ensure garbo-daily.py actually runs."""
        rv, out, err = run_script(
            "cronscripts/garbo-daily.py", ["-q"], expect_returncode=0)
        self.failIf(out.strip(), "Output to stdout: %s" % out)
        self.failIf(err.strip(), "Output to stderr: %s" % err)
        DatabaseLayer.force_dirty_database()

    def test_hourly_script(self):
        """Ensure garbo-hourly.py actually runs."""
        rv, out, err = run_script(
            "cronscripts/garbo-hourly.py", ["-q"], expect_returncode=0)
        self.failIf(out.strip(), "Output to stdout: %s" % out)
        self.failIf(err.strip(), "Output to stderr: %s" % err)


class TestGarbo(TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestGarbo, self).setUp()
        # Run the garbage collectors to remove any existing garbage,
        # starting us in a known state.
        self.runDaily()
        self.runHourly()

    def runDaily(self):
        LaunchpadZopelessLayer.switchDbUser('garbo-daily')
        collector = DailyDatabaseGarbageCollector(test_args=[])
        collector.logger = QuietFakeLogger()
        collector.main()

    def runHourly(self):
        LaunchpadZopelessLayer.switchDbUser('garbo-hourly')
        collector = HourlyDatabaseGarbageCollector(test_args=[])
        collector.logger = QuietFakeLogger()
        collector.main()

    def test_OAuthNoncePruner(self):
        store = IMasterStore(OAuthNonce)
        now = datetime.utcnow().replace(tzinfo=UTC)
        timestamps = [
            now - timedelta(days=2), # Garbage
            now - timedelta(days=1) - timedelta(seconds=60), # Garbage
            now - timedelta(days=1) + timedelta(seconds=60), # Not garbage
            now, # Not garbage
            ]
        LaunchpadZopelessLayer.switchDbUser('testadmin')

        # Make sure we start with 0 nonces.
        self.failUnlessEqual(store.find(OAuthNonce).count(), 0)

        for timestamp in timestamps:
            OAuthNonce(
                access_tokenID=1,
                request_timestamp = timestamp,
                nonce = str(timestamp))
        transaction.commit()

        # Make sure we have 4 nonces now.
        self.failUnlessEqual(store.find(OAuthNonce).count(), 4)

        self.runHourly()

        # Now back to two, having removed the two garbage entries.
        self.failUnlessEqual(store.find(OAuthNonce).count(), 2)

        # And none of them are older than a day.
        # Hmm... why is it I'm putting tz aware datetimes in and getting
        # naive datetimes back? Bug in the SQLObject compatibility layer?
        # Test is still fine as we know the timezone.
        self.failUnless(
            store.find(
                Min(OAuthNonce.request_timestamp)).one().replace(tzinfo=UTC)
            >= now - timedelta(days=1))

    def test_OpenIDConsumerNoncePruner(self):
        now = int(time.mktime(time.gmtime()))
        MINUTES = 60
        HOURS = 60 * 60
        DAYS = 24 * HOURS
        timestamps = [
            now - 2 * DAYS, # Garbage
            now - 1 * DAYS - 1 * MINUTES, # Garbage
            now - 1 * DAYS + 1 * MINUTES, # Not garbage
            now, # Not garbage
            ]
        LaunchpadZopelessLayer.switchDbUser('testadmin')

        store = IMasterStore(OpenIDConsumerNonce)

        # Make sure we start with 0 nonces.
        self.failUnlessEqual(store.find(OpenIDConsumerNonce).count(), 0)

        for timestamp in timestamps:
            nonce = store.add(OpenIDConsumerNonce())
            nonce.server_url = unicode(timestamp)
            nonce.timestamp = timestamp
            nonce.salt = u'aa'
            store.add(nonce)
        transaction.commit()

        # Make sure we have 4 nonces now.
        self.failUnlessEqual(store.find(OpenIDConsumerNonce).count(), 4)

        # Run the garbage collector.
        self.runHourly()

        # We should now have 2 nonces.
        self.failUnlessEqual(store.find(OpenIDConsumerNonce).count(), 2)

        # And none of them are older than 1 day
        earliest = store.find(Min(OpenIDConsumerNonce.timestamp)).one()
        self.failUnless(earliest >= now - 24*60*60, 'Still have old nonces')

    def test_CodeImportResultPruner(self):
        now = datetime.utcnow().replace(tzinfo=UTC)
        store = IMasterStore(CodeImportResult)

        def new_code_import_result(timestamp):
            LaunchpadZopelessLayer.switchDbUser('testadmin')
            CodeImportResult(
                date_created=timestamp,
                code_importID=1, machineID=1, requesting_userID=1,
                status=CodeImportResultStatus.FAILURE,
                date_job_started=timestamp)
            transaction.commit()

        new_code_import_result(now - timedelta(days=60))
        new_code_import_result(now - timedelta(days=19))
        new_code_import_result(now - timedelta(days=20))
        new_code_import_result(now - timedelta(days=21))

        # Run the garbage collector
        self.runDaily()

        # Nothing is removed, because we always keep the 4 latest.
        self.failUnlessEqual(
            store.find(CodeImportResult).count(), 4)

        new_code_import_result(now - timedelta(days=31))
        self.runDaily()
        self.failUnlessEqual(
            store.find(CodeImportResult).count(), 4)

        new_code_import_result(now - timedelta(days=29))
        self.runDaily()
        self.failUnlessEqual(
            store.find(CodeImportResult).count(), 4)

        # We now have no CodeImportResults older than 30 days
        self.failUnless(
            store.find(
                Min(CodeImportResult.date_created)).one().replace(tzinfo=UTC)
            >= now - timedelta(days=30))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
