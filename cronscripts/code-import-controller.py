#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

"""Start import jobs if required and possible."""

import _pythonpath

from canonical.launchpad.codehosting.codeimport.controller import (
    CodeImportController)
from canonical.launchpad.scripts.base import LaunchpadCronScript


class CodeImportControllerScript(LaunchpadCronScript):
    usage = '%prog'

    def main(self):
        CodeImportController(self.logger).dispatchJobs()


if __name__ == '__main__':
    script = CodeImportController(
        'code-import-controller', dbuser='importd')
    script.lock_and_run()

