# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests of PendingCodeMail"""

__metaclass__ = type

import unittest

from canonical.testing import LaunchpadFunctionalLayer

from canonical.launchpad.interfaces import IPendingCodeMail
from canonical.launchpad.database import PendingCodeMail
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.testing import verifyObject


class TestPendingCodeMail(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_ProvidesInterface(self):
        mail = self.factory.makePendingCodeMail()
        verifyObject(IPendingCodeMail, mail)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
