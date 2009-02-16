# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Runs the archivepublisher doctests."""

__metaclass__ = type

import logging
import unittest

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.ftests import login, logout
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setGlobs, setUp, tearDown)
from canonical.testing import LaunchpadZopelessLayer


def archivePublisherSetUp(test):
    setUp(test)
    LaunchpadZopelessLayer.switchDbUser(config.archivepublisher.dbuser)


def test_suite():
    return LayeredDocFileSuite(
       'deathrow.txt',
       setUp=archivePublisherSetUp,
       tearDown=tearDown,
       layer=LaunchpadZopelessLayer,
       stdout_logging_level=logging.WARNING
       )


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
