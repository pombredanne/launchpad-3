#!/usr/bin/python2.4 -u

import _pythonpath

import logging
import sys
import time
import xmlrpclib

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.branchfsclient import (
    BlockingProxy, BranchFileSystemClient)
from canonical.codehosting.transport import _extractResult
from canonical.config import config
from canonical.launchpad.interfaces.codehosting import (
    BRANCH_TRANSPORT, LAUNCHPAD_SERVICES)
from canonical.launchpad.scripts.base import LaunchpadScript

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename='/tmp/gooble')

log = logging.getLogger('BranchRewrite')

s = BlockingProxy(xmlrpclib.ServerProxy(config.codehosting.branchfs_endpoint))
c = BranchFileSystemClient(s, LAUNCHPAD_SERVICES, 1.0)

def t(path):
    return _extractResult(c.translatePath(path))

class BranchRewriter(LaunchpadScript):

    def run(self, use_web_security=False, implicit_begin=True,
            isolation=None):
        """See `LaunchpadScript.run`.

        We override to avoid all of the setting up all of the component
        architecture and connecting to the database.
        """
        self.main()

    def main(self):
        log.debug("Starting up...")
        while True:
            try:
                line = sys.stdin.readline().strip()
                T = time.time()
                trailingSlash = line.endswith('/')
                transport_type, info, trailing = t(line)
                if transport_type == BRANCH_TRANSPORT:
                    if trailing.startswith('.bzr'):
                        r = '/' + branch_id_to_path(info['id']) + '/' + trailing
                        if trailingSlash:
                            r += '/'
                    else:
                        r = 'http://localhost:8080' + line
                    log.debug("%r -> %r (%fs)", line, r, time.time() - T)
                    print r
                else:
                    print "NULL"
            except:
                log.exception('oops')
                print "NULL"


if __name__ == '__main__':
    BranchRewriter("branch-rewrite").run()
