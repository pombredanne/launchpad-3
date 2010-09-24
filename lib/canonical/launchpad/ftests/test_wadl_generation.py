# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the web service WADL and HTML generation APIs."""

__metaclass__ = type

import pkg_resources
import shutil
import subprocess
import tempfile

from zope.component import getUtility

from canonical.launchpad.rest.wadl import generate_wadl, generate_html
from canonical.launchpad.systemhomes import WebServiceApplication
from canonical.testing import LaunchpadFunctionalLayer
from lazr.restful.interfaces import IWebServiceConfiguration
from lp.testing import TestCase
from lp.testing.matchers import (
    StartsWith,
    Contains,
    )


class SmokeTestWadlAndDocGeneration(TestCase):
    """Smoke test the WADL and HTML generation front-end functions."""

    layer = LaunchpadFunctionalLayer

    def test_wadl(self):
        config = getUtility(IWebServiceConfiguration)
        for version in config.active_versions:
            wadl = generate_wadl(version)
            self.assertThat(wadl[:40], StartsWith('<?xml '))


    def test_html(self):
        config = getUtility(IWebServiceConfiguration)
        stylesheet = pkg_resources.resource_filename(
            'launchpadlib', 'wadl-to-refhtml.xsl')
        for version in config.active_versions:
            wadl_filename = WebServiceApplication.cachedWADLPath(
                'development', version)
            html = generate_html(wadl_filename)
            self.assertThat(html[:999], Contains('<html '))

    def test_subprocess_error(self):
        # If the execution of xsltproc fails, an exception is raised.
        self.assertRaises(
            subprocess.CalledProcessError, generate_html, 'does-not-exist')
