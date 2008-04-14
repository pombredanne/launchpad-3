# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0401,C0301

from unittest import TestCase

from canonical.database.sqlbase import cursor
from canonical.testing import LaunchpadZopelessLayer

from canonical.launchpad.ftests import login
from canonical.launchpad.testing.factory import *


class TestCaseWithFactory(TestCase):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        login('test@canonical.com')
        self.factory = LaunchpadObjectFactory()

    def assertIsDBNow(self, value):
        """Assert supplied value equals database time.

        The database time is the same for the whole transaction, and may
        not match the current time exactly.
        :param value: A datetime that is expected to match the current
            database time.
        """
        # XXX Probably does not belong here, but better location not clear.
        # Used primarily for testing ORM objects, which ought to use factory.
        cur = cursor()
        cur.execute("SELECT CURRENT_TIMESTAMP AT TIME ZONE 'UTC';")
        [database_now] = cur.fetchone()
        self.assertEqual(
            database_now.utctimetuple(), value.utctimetuple())
