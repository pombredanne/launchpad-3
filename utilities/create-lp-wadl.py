#! /usr/bin/python2.5
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Create a static WADL file describing the current webservice.

Usage hint:

% LPCONFIG="edge" utilities/create-lp-wadl.py launchpad-%(version)s.wadl
"""

import _pythonpath

import sys
import urlparse

from zope.component import getUtility

from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.webapp.servers import (
    WebServicePublication, WebServiceTestRequest)
from canonical.launchpad.webapp.vhosts import allvhosts
from canonical.launchpad.systemhomes import WebServiceApplication
from lazr.restful.interfaces import IWebServiceConfiguration

def main(path_template):
    WebServiceApplication.cached_wadl = {} # do not use cached file version
    execute_zcml_for_scripts()
    config = getUtility(IWebServiceConfiguration)

    # Request the WADL from the root resource.
    # We do this by creating a request object asking for a WADL
    # representation.
    for version in config.active_versions:
        url = urlparse.urljoin(allvhosts.configs['api'].rooturl, version)
        print "URL: " + url
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
        login(ANONYMOUS, request)
        filename = path_template % {'version' : version}
        print "Writing WADL for version %s to %s." % (version, filename)
        f = open(filename, 'w')
        content = request.publication.getApplication(request)(request)
        f.write(content)
        f.close()
    return 0

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "Usage: %s [WADL path template]" % sys.argv[0]
        print " Example: %s path/to/wadl/wadl-%%(version).xml" % (
            sys.argv[0])
        sys.exit(-1)
    sys.exit(main(sys.argv[1]))
