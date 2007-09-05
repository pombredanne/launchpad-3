# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for BranchURIField."""

__metaclass__ = type
__all__ = []


import unittest

from canonical.config import config
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.interfaces.branch import BranchURIField
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.webapp.vhosts import allvhosts


class TestBranchURIField(LaunchpadZopelessTestCase):
    """Test the validation logic for Branch URI fields.

    Users can register their external Bazaar branches on Launchpad by providing
    a URI. Launchpad will then attempt to mirror those branches to the
    supermirror.

    Many valid URIs are not valid branch URIs. In particular, anything URI that
    points to Launchpad is invalid, because all of the URIs for branches on
    Launchpad are generated from database fields and are thus subject to
    change. Further, branches cannot be on the root of a site, nor are users
    allowed to register a branch that is already being mirrored.
    """

    def setUp(self):
        LaunchpadZopelessTestCase.setUp(self)
        self.field = BranchURIField()

    def listLaunchpadDomains(self):
        """Iterate over each of the configured domains of Launchpad."""
        mainsite = allvhosts.configs['mainsite'].hostname
        for vhost in allvhosts.configs.values():
            if vhost.hostname.endswith(mainsite):
                yield vhost.hostname

    def assertInvalid(self, uri):
        """Assert the given URL is considered invalid by BranchURIField."""
        self.assertRaises(LaunchpadValidationError, self.field.validate, uri)

    def test_notFromSupermirror(self):
        # Branches on the supermirror are already registered, so there is no
        # need to register them, again.
        self.assertInvalid(
            u'%s/~user/+junk/branch' % config.launchpad.supermirror_root)

    def test_notFromLaunchpad(self):
        # URIs from Launchpad itself are invalid, no matter what the subdomain.
        for domain in self.listLaunchpadDomains():
            self.assertInvalid(u'http://%s/user/+junk/branch' % domain)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
