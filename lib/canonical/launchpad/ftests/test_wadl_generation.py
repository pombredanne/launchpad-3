# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the checked-in WADL."""

__metaclass__ = type

import os.path
import pkg_resources
import unittest

from zope.component import getUtility

from canonical.launchpad.rest.wadl import generate_wadl, generate_html
from canonical.launchpad.systemhomes import WebServiceApplication
from canonical.testing import LaunchpadFunctionalLayer
from lazr.restful.interfaces import IWebServiceConfiguration


class SmokeTestWadlAndDocGeneration(unittest.TestCase):
    """Smoke test the WADL and HTML generation front-end functions."""

    layer = LaunchpadFunctionalLayer

    def test_wadl(self):
        config = getUtility(IWebServiceConfiguration)
        for version in config.active_versions:
            wadl = generate_wadl(version)
            self.assert_(wadl.startswith('<?xml '))

    def test_html(self):
        config = getUtility(IWebServiceConfiguration)
        stylesheet = pkg_resources.resource_filename(
            'launchpadlib', 'wadl-to-refhtml.xsl')
        for version in config.active_versions:
            wadl_filename = WebServiceApplication.cachedWADLPath(
                'development', version)
            html = generate_html(wadl_filename)
            self.assert_('<html ' in html)
