#!/usr/bin/python2.4
"""Upload processor.

Given a bunch of context information and a bunch of files, process them as
an upload to a distro/whatever within the launchpad.
"""

import os
import _pythonpath

from canonical.archiveuploader.uploadpolicy import policy_options
from canonical.archiveuploader.uploadprocessor import UploadProcessor
from canonical.config import config
from canonical.launchpad.scripts.base import (
    LaunchpadScript, LaunchpadScriptFailure)


class ProcessUpload(LaunchpadScript):

    def add_my_options(self):
        self.parser.add_option(
            "-n", "--dry-run", action="store_true",
            dest="dryrun", metavar="DRY_RUN", default=False,
            help=("Whether to treat this as a dry-run or not."
                  "Also implies -KM."))

        self.parser.add_option(
            "-K", "--keep", action="store_true",
            dest="keep", metavar="KEEP", default=False,
            help="Whether to keep or not the uploads directory.")

        self.parser.add_option(
            "-M", "--no-mails", action="store_true",
            dest="nomails", default=False,
            help="Whether to suppress the sending of mails or not.")

        self.parser.add_option(
            "-J", "--just-leaf", action="store", dest="leafname",
            default=None, help="A specific leaf dir to limit to.",
            metavar = "LEAF")
        policy_options(self.parser)

    def main(self):
        if not self.args:
            raise LaunchpadScriptFailure(
                "Need to be given exactly one non-option "
                "argument, namely the fsroot for the upload.")

        self.options.base_fsroot = os.path.abspath(self.args[0])

        if not os.path.isdir(self.options.base_fsroot):
            raise LaunchpadScriptFailure(
                "%s is not a directory" % self.options.base_fsroot)

        self.logger.debug("Initialising connection.")
        UploadProcessor(
            self.options, self.txn, self.logger).processUploadQueue()

    @property
    def lockfilename(self):
        """Return specific lockfilename according the policy used.

        Each different p-u policy requires and uses a different lockfile.
        This is because they are run by different users and are independent
        of each other.
        """
        return "process-upload-%s.lock" % self.options.context

if __name__ == '__main__':
    script = ProcessUpload('process-upload', dbuser=config.uploader.dbuser)
    script.lock_and_run()

