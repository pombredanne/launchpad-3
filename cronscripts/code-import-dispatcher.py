#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

""" """


import _pythonpath

from canonical.codehosting.codeimport.dispatcher import CodeImportDispatcher
from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.webapp.errorlog import globalErrorUtility


class CodeImportDispatcherScript(LaunchpadCronScript):

    def main(self):
        globalErrorUtility.configure('codeimportdispatcher')

        CodeImportDispatcher(self.logger).dispatchJobs()


if __name__ == '__main__':
    script = CodeImportDispatcher(
        "codeimportdispatcher", dbuser=config.codeimportdispatcher.dbuser)
    script.lock_and_run()

