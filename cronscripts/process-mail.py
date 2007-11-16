#!/usr/bin/python2.4
# Copyright 2004 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403
"""Fetches mail from the mail box and feeds them to the handlers."""

import _pythonpath

from zope.component.exceptions import ComponentLookupError

from canonical.launchpad.scripts.base import (
    LaunchpadCronScript, LaunchpadScriptFailure)
from canonical.launchpad.mail.incoming import handleMail
from canonical.launchpad.interfaces import IMailBox

class ProcessMail(LaunchpadCronScript):
    usage = """%prog [options]

    """ + __doc__
    def main(self):
        try:
            handleMail(self.txn)
        except ComponentLookupError, lookup_error:
            if lookup_error.args[0] != IMailBox:
                raise
            raise LaunchpadScriptFailure(
                "No mail box is configured. "
                "Please see mailbox.txt for info on how to configure one.")


if __name__ == '__main__':
    script = ProcessMail('process-mail')
    script.lock_and_run(use_web_security=True)

