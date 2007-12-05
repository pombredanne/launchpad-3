# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for the checkwatches remote bug synchronisation code."""

__metaclass__ = type
__all__ = []

from unittest import TestLoader

from canonical.config import config
from canonical.database.sqlbase import commit
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase

class TestCheckwatches(LaunchpadZopelessTestCase):
    """Tests for the bugwatch updating system."""

def test_suite():
    return TestLoader().loadTestsFromName(__name__)
