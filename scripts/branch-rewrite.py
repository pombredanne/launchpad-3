#!/usr/bin/python2.4 -u
# pylint: disable-msg=W0403

"""Script intended to run as a :prg: RewriteMap.

See http://httpd.apache.org/docs/2.2/mod/mod_rewrite.html#rewritemap for the
documentation of the very simple 'protocol' Apache uses to talk to us, and
lp.codehosting.rewrite.BranchRewriter for the logic of the rewritemap.
"""

import _pythonpath

import sys
import xmlrpclib

from lp.codehosting.vfs import BlockingProxy
from lp.codehosting.rewrite import BranchRewriter
from canonical.config import config
from lp.services.scripts.base import LaunchpadScript


class BranchRewriteScript(LaunchpadScript):

    def __init__(self, name):
        LaunchpadScript.__init__(self, name)
        proxy = xmlrpclib.ServerProxy(config.codehosting.branchfs_endpoint)
        self.rewriter = BranchRewriter(self.logger, BlockingProxy(proxy))

    def add_my_options(self):
        """Make the logging go to a file by default.

        Because this script is run by Apache, logging to stderr results in our
        log output ending up in Apache's error.log, which is not so useful.
        We hack the OptionParser to set the default (which will be applied;
        Apache doesn't pass any arguments to the script it starts up) to a
        value from the config.
        """
        log_file_location = config.codehosting.rewrite_script_log_file
        self.parser.defaults['log_file'] = log_file_location

    def run(self, use_web_security=False, implicit_begin=True,
            isolation=None):
        """See `LaunchpadScript.run`.

        As this script does not need the component architecture or a
        connection to the database, we override this method to avoid setting
        them up.
        """
        self.main()

    def main(self):
        self.logger.debug("Starting up...")
        while True:
            try:
                line = sys.stdin.readline()
                # Mod-rewrite always gives us a newline terminated string.
                if line:
                    print self.rewriter.rewriteLine(line.strip())
                else:
                    # Standard input has been closed, so die.
                    return
            except KeyboardInterrupt:
                sys.exit()
            except:
                self.logger.exception('Exception occurred:')
                print "NULL"


if __name__ == '__main__':
    BranchRewriteScript("branch-rewrite").run()
