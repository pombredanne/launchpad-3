# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test mail documentation."""

__metaclass__ = type

import os

from zope.security.management import setSecurityPolicy

from canonical.config import config
from canonical.launchpad.ftests import login
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
special = {}


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

    doctests = [
        '../../../answers/tests/emailinterface.txt',
        '../../../bugs/tests/bugs-emailinterface.txt',
        '../../../bugs/doc/bugs-email-affects-path.txt',
        '../doc/emailauthentication.txt',
        ]

    @classmethod
    def addTestsToSpecial(cls):
        """Adds all the tests related to process-mail.py to special"""
        for filepath in cls.doctests:
            filename = os.path.basename(filepath)
            special[filename] = LayeredDocFileSuite(
                filepath,
                setUp=setUp, tearDown=tearDown,
                layer=cls,
                stdout_logging=False)

        # Adds a copy of some bug doctests that will be run with
        # the processmail user.
        def bugSetStatusSetUp(test):
            setUp(test)
            test.globs['test_dbuser'] = config.processmail.dbuser

        special['bug-set-status.txt-processmail'] = LayeredDocFileSuite(
                '../../../bugs/doc/bug-set-status.txt',
                setUp=bugSetStatusSetUp, tearDown=tearDown,
                layer=cls,
                stdout_logging=False)

        def bugmessageSetUp(test):
            setUp(test)
            login('no-priv@canonical.com')

        special['bugmessage.txt-processmail'] = LayeredDocFileSuite(
                '../../../bugs/doc/bugmessage.txt',
                setUp=bugmessageSetUp, tearDown=tearDown,
                layer=cls,
                stdout_logging=False)


ProcessMailLayer.addTestsToSpecial()


def test_suite():
    suite = build_test_suite(here, special, layer=DatabaseFunctionalLayer)
    return suite
