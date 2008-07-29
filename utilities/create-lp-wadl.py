#! /usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Create a static WADL file describing the current webservice.

Usage hint:

% LPCONFIG="edge" utilities/create-lp-wadl.py > launchpad.wadl
"""

import _pythonpath

import sys

from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.webapp.servers import (
    WebServicePublication, WebServiceTestRequest)
from canonical.launchpad.webapp.vhosts import allvhosts

def main():
    execute_zcml_for_scripts()

    # Request the WADL from the root resource.
    request = WebServiceTestRequest(environ={
        'SERVER_URL': allvhosts.configs['api'].rooturl,
        'HTTP_HOST': allvhosts.configs['api'].hostname,
        'HTTP_ACCEPT': 'application/vd.sun.wadl+xml'
        })
    request.setPublication(WebServicePublication(None))
    login(ANONYMOUS, request)
    print request.publication.getApplication(request)(request)

    return 0

if __name__ == '__main__':
    sys.exit(main())
