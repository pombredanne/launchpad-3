# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the checked-in WADL."""

__metaclass__ = type

import os.path
import pkg_resources
import subprocess
import unittest
import urlparse

from zope.component import getUtility

from canonical.launchpad.webapp.interaction import (
    ANONYMOUS, setupInteractionByEmail)
from canonical.launchpad.webapp.servers import (
    WebServicePublication, WebServiceTestRequest)
from canonical.launchpad.systemhomes import WebServiceApplication
from canonical.launchpad.webapp.vhosts import allvhosts
from canonical.testing import LaunchpadFunctionalLayer
from lazr.restful.interfaces import IWebServiceConfiguration


def generate_wadl(version):
    url = urlparse.urljoin(allvhosts.configs['api'].rooturl, version)
    # The generated WADL prescribes HTTPS, so we want to force it's use here.
    url = url.replace('http://', 'https://')

    # Unfortunately running a request is the best way to generate the WADL.
    request = WebServiceTestRequest(version=version, environ={
        'SERVER_URL': url,
        'HTTP_HOST': allvhosts.configs['api'].hostname,
        'HTTP_ACCEPT': 'application/vd.sun.wadl+xml',
        })
    request.setPublication(WebServicePublication(None))
    setupInteractionByEmail(ANONYMOUS, request)
    return request.publication.getApplication(request)(request)


class TestCheckedInWadlAndDocs(unittest.TestCase):
    """As an optimization we check in some web service related files

    ...but that creates the chance that what is checked in will vary from what
    is generated.  These tests make sure that the WADL and HTML on-disk is in
    sync with that which is generated.

    If these tests are failing and you just changed the web service, you
    probably need to regenerate the WADL and check it in.  At the time of this
    writing, this is the command to regenerate the files (copy pastable):

    LPCONFIG=development bin/py ./utilities/create-lp-wadl-and-apidoc.py \
    "lib/canonical/launchpad/apidoc/wadl-development-%(version)s.xml" --force

    You could also delete the files an re-run make.
    """

    layer = LaunchpadFunctionalLayer

    def test_wadl(self):
        # Verify that the generated WADL matches that which is checked in.
        config = getUtility(IWebServiceConfiguration)
        for version in config.active_versions:
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
            wadl_filename = WebServiceApplication.cachedWADLPath(
                'development', version)
            html_filename = os.path.join(
                os.path.dirname(wadl_filename), version + '.html')
            html_on_disk = open(html_filename).read()
            generated_html = subprocess.Popen(
                ['xsltproc', stylesheet, wadl_filename],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE).communicate()[0]

            assert generated_html, 'no HTML was generated'
            self.assertEqual(html_on_disk, generated_html)
