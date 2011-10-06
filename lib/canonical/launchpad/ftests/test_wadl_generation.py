# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the web service WADL and HTML generation APIs."""

__metaclass__ = type

from testtools.matchers import StartsWith

from zope.component import getUtility

from canonical.launchpad.rest.wadl import (
    generate_json,
    generate_wadl,
    )
from canonical.testing import LaunchpadFunctionalLayer
from lazr.restful.interfaces import IWebServiceConfiguration
from lp.testing import TestCase


class SmokeTestWadlAndDocGeneration(TestCase):
    """Smoke test the WADL and HTML generation front-end functions."""

    layer = LaunchpadFunctionalLayer

    def test_wadl(self):
        config = getUtility(IWebServiceConfiguration)
        for version in config.active_versions:
            wadl = generate_wadl(version)
            self.assertThat(wadl[:40], StartsWith('<?xml '))

    def test_json(self):
        config = getUtility(IWebServiceConfiguration)
        for version in config.active_versions:
            json = generate_json(version)
            self.assertThat(json, StartsWith('{"'))
