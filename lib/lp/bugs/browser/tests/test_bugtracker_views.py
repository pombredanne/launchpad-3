# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugTracker views."""

__metaclass__ = type

import unittest

from datetime import datetime, timedelta
from pytz import utc

from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.bugs.browser.bugtracker import (
    BugTrackerEditView)
from lp.registry.interfaces.person import IPersonSet
from lp.testing import login, TestCaseWithFactory
from lp.testing.sampledata import ADMIN_EMAIL, NO_PRIVILEGE_EMAIL
from lp.testing.views import create_initialized_view



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
