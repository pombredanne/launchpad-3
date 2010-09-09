# Copyright 2010 Canonical Ltd.  This software is licensed under the
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


class TestCheckedInWadlAndDocs(unittest.TestCase):
    """As an optimization and safety net we check in some web service files

    The optimization is that it takes less time to build because the non-devel
    WADL files and HTML documentaiton don't have to be regenerated.  It is a
    safety net because it is our policy (as of the time of this writing) that
    the non-devel APIs should not change (even in backward-compatible ways),
    therefore the WADL files describing the APIs -- and generated from
    descriptions of the APIs -- should not change either.

    If these tests are failing and you just changed the web service, you
    probably need to add version specifiers to your changes to limit their scope.

    If you fixed a bug in a non-devel version of the web service API, then you
    will need to regenerate the WADL and check it in.  At the time of this
    writing, this is the command to regenerate the files (copy pastable):

    LPCONFIG=development bin/py ./utilities/create-lp-wadl-and-apidoc.py \
    "lib/canonical/launchpad/apidoc/wadl-development-%(version)s.xml" --force

    You could also delete the offending files and re-run make.
    """

    layer = LaunchpadFunctionalLayer

    def test_wadl(self):
        # Verify that the generated WADL matches that which is checked in.
        config = getUtility(IWebServiceConfiguration)
        for version in config.active_versions:
            if version == 'devel':
                continue
            wadl_filename = WebServiceApplication.cachedWADLPath(
                'development', version)
            wadl_on_disk = open(wadl_filename).read()
            generated_wadl = generate_wadl(version)
            self.assertEqual(wadl_on_disk, generated_wadl)

    def test_html(self):
        # Verify that the generated HTML matches that which is checked in.
        config = getUtility(IWebServiceConfiguration)
        stylesheet = pkg_resources.resource_filename(
            'launchpadlib', 'wadl-to-refhtml.xsl')
        for version in config.active_versions:
            # only non-devel versions are frozen
            if version == 'devel':
                continue
            wadl_filename = WebServiceApplication.cachedWADLPath(
                'development', version)
            html_filename = os.path.join(
                os.path.dirname(wadl_filename), version + '.html')
            html_on_disk = open(html_filename).read()
            generated_html = generate_html(wadl_filename)

            assert generated_html, 'no HTML was generated'
            self.assertEqual(html_on_disk, generated_html)
