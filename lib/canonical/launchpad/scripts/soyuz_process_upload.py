# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Upload processor for Soyuz."""

__metaclass__ = type
__all__ = ['ProcessUpload']

import os

from canonical.archiveuploader.uploadprocessor import UploadProcessor
from canonical.launchpad.scripts.base import (
    LaunchpadScript, LaunchpadScriptFailure)


class ProcessUpload(LaunchpadScript):
    """`LaunchpadScript` wrapper for `UploadProcessor`."""

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

        self.parser.add_option(
            "-C", "--context", action="store", dest="context",
            metavar="CONTEXT", default="insecure",
            help="The context in which to consider the upload.")

        self.parser.add_option(
            "-d", "--distro", action="store", dest="distro", metavar="DISTRO",
            default="ubuntu", help="Distribution to give back from")

        self.parser.add_option(
            "-s", "--series", action="store", default=None,
            dest="distroseries", metavar="DISTROSERIES",
            help="Distro series to give back from.")

        self.parser.add_option(
            "-b", "--buildid", action="store", type="int", dest="buildid",
            metavar="BUILD",
            help="The build ID to which to attach this upload.")

        self.parser.add_option(
            "-a", "--announce", action="store", dest="announcelist",
            metavar="ANNOUNCELIST", help="Override the announcement list")

    def main(self):
        if len(self.args) != 1:
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


