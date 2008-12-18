#!/usr/bin/python2.4 -u
# pylint: disable-msg=W0403

import _pythonpath

import sys
import xmlrpclib

from canonical.codehosting.branchfsclient import BlockingProxy
from canonical.codehosting.rewrite import BranchRewriter
from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadScript

# XXX logging!

class BranchRewriteScript(LaunchpadScript):

    def __init__(self, name):
        LaunchpadScript.__init__(self, name)
        proxy = xmlrpclib.ServerProxy(config.codehosting.branchfs_endpoint)
        self.rewriter = BranchRewriter(self.logger, BlockingProxy(proxy))

    def run(self, use_web_security=False, implicit_begin=True,
            isolation=None):
        """See `LaunchpadScript.run`.

        We override to avoid all of the setting up all of the component
        architecture and connecting to the database.
        """
        self.main()

    def main(self):
        self.logger.debug("Starting up...")
        while True:
            try:
                line = sys.stdin.readline().strip()
                print self.rewriter.rewriteLine(line)
            except KeyboardInterrupt:
                sys.exit()
            except:
                self.logger.exception('oops')
                print "NULL"


if __name__ == '__main__':
    BranchRewriteScript("branch-rewrite").run()
