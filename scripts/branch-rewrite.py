#!/usr/bin/python2.4 -u

import _pythonpath

import logging
import sys
import time
import xmlrpclib

from canonical.codehosting import branch_id_to_path
from canonical.config import config

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename='/tmp/gooble')

log = logging.getLogger('BranchRewrite')

log.debug("Starting up...")

s = xmlrpclib.ServerProxy(config.codehosting.branchfs_endpoint)

while True:
    try:
        line = sys.stdin.readline().strip()
        T = time.time()
        trailingSlash = line.endswith('/')
        log.info(repr(line))
        transport_type, info, trailing = s.translatePath(
            "+launchpad-services", line)
        if transport_type == 'BRANCH_TRANSPORT':
            if trailing.startswith('.bzr'):
                r = '/' + branch_id_to_path(info['id']) + '/' + trailing
                if trailingSlash:
                    r += '/'
            else:
                r = 'http://localhost:8080' + line
        log.debug("%r -> %r (%fs)", line, r, time.time() - T)
        print r
    except:
        log.exception('oops')
        print 'notfound'
