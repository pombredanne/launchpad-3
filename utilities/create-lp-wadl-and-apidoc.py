#! /usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Create a static WADL file describing the current webservice.

Usage hint:

% LPCONFIG="edge" utilities/create-lp-wadl.py launchpad-%(version)s.wadl
"""

import _pythonpath

import os
import pkg_resources
import subprocess
import sys
import urlparse

from zope.component import getUtility
from zope.pagetemplate.pagetemplatefile import PageTemplateFile

from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.webapp.interaction import (
    ANONYMOUS, setupInteractionByEmail)
from canonical.launchpad.webapp.servers import (
    WebServicePublication, WebServiceTestRequest)
from canonical.launchpad.webapp.vhosts import allvhosts
from canonical.launchpad.systemhomes import WebServiceApplication
from lazr.restful.interfaces import IWebServiceConfiguration


def main(path_template):
    WebServiceApplication.cached_wadl = None # do not use cached file version
    execute_zcml_for_scripts()
    config = getUtility(IWebServiceConfiguration)
    directory, ignore = os.path.split(path_template)

    stylesheet = pkg_resources.resource_filename(
        'launchpadlib', 'wadl-to-refhtml.xsl')

    # First, create an index.html with links to all the HTML
    # documentation files we're about to generate.
    template_file = 'apidoc-index.pt'
    template = PageTemplateFile(template_file)
    f = open(os.path.join(directory, "index.html"), 'w')
    f.write(template(config=config))

    # Request the WADL from the root resource.
    # We do this by creating a request object asking for a WADL
    # representation.
    for version in config.active_versions:
        url = urlparse.urljoin(allvhosts.configs['api'].rooturl, version)
        request = WebServiceTestRequest(version=version, environ={
            'SERVER_URL': url,
            'HTTP_HOST': allvhosts.configs['api'].hostname,
            'HTTP_ACCEPT': 'application/vd.sun.wadl+xml'
            })
        # We then bypass the usual publisher processing by associating
        # the request with the WebServicePublication (usually done  by the
        # publisher) and then calling the root resource - retrieved through
        # getApplication().
        request.setPublication(WebServicePublication(None))
        setupInteractionByEmail(ANONYMOUS, request)
        filename = path_template % {'version' : version}
        print "Writing WADL for version %s to %s." % (version, filename)
        f = open(filename, 'w')
        content = request.publication.getApplication(request)(request)
        f.write(content)
        f.close()

        # Now, convert the WADL into an human-readable description and
        # put the HTML in the same directory as the WADL.
        html_filename = os.path.join(directory, version + ".html")
        print "Writing apidoc for version %s to %s" % (
            version, html_filename)
        stdout = open(html_filename, "w")
        subprocess.Popen(['xsltproc', stylesheet, filename], stdout=stdout)
        stdout.close()

    return 0

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "Usage: %s [WADL path template]" % sys.argv[0]
        print " Example: %s path/to/wadl/wadl-%%(version).xml" % (
            sys.argv[0])
        sys.exit(-1)
    sys.exit(main(sys.argv[1]))
