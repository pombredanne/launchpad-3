#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Look for and dispatch code import jobs as needed."""

# pylint: disable-msg=W0403
import _pythonpath

from xmlrpclib import ServerProxy

from canonical.codehosting.codeimport.dispatcher import CodeImportDispatcher
from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.webapp.errorlog import globalErrorUtility


class CodeImportDispatcherScript(LaunchpadScript):

    def run(self, use_web_security=False, implicit_begin=True,
            isolation=None):
        """See `LaunchpadScript.run`.

        We override to avoid all of the setting up all of the component
        architecture and connecting to the database.
        """
        self.main()

    def main(self):
        globalErrorUtility.configure('codeimportdispatcher')

        self.logger.debug("endpoint: %s", config.codeimportdispatcher.codeimportscheduler_url)

        CodeImportDispatcher(self.logger).findAndDispatchJob(
            ServerProxy(config.codeimportdispatcher.codeimportscheduler_url))


if __name__ == '__main__':
    script = CodeImportDispatcherScript("codeimportdispatcher")
    script.lock_and_run()

