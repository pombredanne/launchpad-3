#!/usr/bin/python2.4 -u

import _pythonpath

import sys
import time
import xmlrpclib

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.branchfsclient import (
    BlockingProxy, BranchFileSystemClient)
from canonical.codehosting.transport import extract_result
from canonical.config import config
from canonical.launchpad.ftests import ANONYMOUS
from canonical.launchpad.interfaces.codehosting import (
    BRANCH_TRANSPORT)
from canonical.launchpad.scripts.base import LaunchpadScript


class BranchRewriter(LaunchpadScript):

    def __init__(self, name):
        LaunchpadScript.__init__(self, name)
        proxy = BlockingProxy(
            xmlrpclib.ServerProxy(config.codehosting.branchfs_endpoint))
        self.client = BranchFileSystemClient(proxy, ANONYMOUS, 1.0)

    def run(self, use_web_security=False, implicit_begin=True,
            isolation=None):
        """See `LaunchpadScript.run`.

        We override to avoid all of the setting up all of the component
        architecture and connecting to the database.
        """
        self.main()

    def translateLine(self, line):
        T = time.time()
        trailingSlash = line.endswith('/')
        deferred = self.client.translatePath(line)
        transport_type, info, trailing = extract_result(deferred)
        if transport_type == BRANCH_TRANSPORT:
            if trailing.startswith('.bzr'):
                r = '/' + branch_id_to_path(info['id']) + '/' + trailing
                if trailingSlash:
                    r += '/'
            else:
                r = config.codehosting.internal_codebrowse_root + line
            self.logger.info("%r -> %r (%fs)", line, r, time.time() - T)
            return r
        else:
            return "NULL"

    def main(self):
        self.logger.debug("Starting up...")
        while True:
            try:
                line = sys.stdin.readline().strip()
                print self.translateLine(line)
            except:
                self.logger.exception('oops')
                print "NULL"


if __name__ == '__main__':
    BranchRewriter("branch-rewrite").run()
