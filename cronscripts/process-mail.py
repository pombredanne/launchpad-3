#!/usr/bin/env python
# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Fetches mail from the mail box and feeds them to the handlers."""

import _pythonpath

import logging, sys
from optparse import OptionParser

from zope.component.exceptions import ComponentLookupError

from canonical.lp import initZopeless
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.mail.incoming import handleMail
from canonical.launchpad.interfaces import IMailBox

usage = """%prog [options]

""" + __doc__

def main(args):
    options_parser = OptionParser(usage=usage)
    logger_options(options_parser)
    options, args = options_parser.parse_args(args)
    
    log = logger('process-mail')

    lockfile = LockFile('/var/lock/launchpad-process-mail.lock', logger=log)
    lockfile.acquire()

    try:
        trans = initZopeless()
        execute_zcml_for_scripts(use_web_security=True)

        try:
            handleMail(trans)
            return 0
        except ComponentLookupError, lookup_error:
            if lookup_error.args[0] == IMailBox:
                log.error(
                    "No mail box is configured. "
                    "Please see mailbox.txt for info on how to configure one.")
                return 1
            raise
    finally:
        lockfile.release()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
