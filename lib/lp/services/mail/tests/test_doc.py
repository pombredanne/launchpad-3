# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test mail documentation."""

__metaclass__ = type

import os

from zope.security.management import setSecurityPolicy

from canonical.config import config
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.services.testing import build_test_suite


here = os.path.dirname(os.path.realpath(__file__))


class ProcessMailLayer(LaunchpadZopelessLayer):
    """Layer containing the tests running inside process-mail.py."""

    @classmethod
    def testSetUp(cls):
        """Fixture replicating the process-mail.py environment.

        This zopeless script uses the regular security policy and
        connects as a specific DB user.
        """
        cls._old_policy = setSecurityPolicy(LaunchpadSecurityPolicy)
        LaunchpadZopelessLayer.switchDbUser(config.processmail.dbuser)

    @classmethod
    def testTearDown(cls):
        """Tear down the test fixture."""
        setSecurityPolicy(cls._old_policy)


special = {
    'emailauthentication.txt': LayeredDocFileSuite(
        '../doc/emailauthentication.txt',
        setUp=setUp, tearDown=tearDown,
        layer=ProcessMailLayer,
        stdout_logging=False)
    }


def test_suite():
    suite = build_test_suite(here, special, layer=DatabaseFunctionalLayer)
    return suite
