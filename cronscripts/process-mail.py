#!/usr/bin/env python
# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Fetches mail from the mail box and feeds them to the handlers."""

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

options_parser = OptionParser(usage=usage)

def create_logger():
    logger = logging.getLogger('process-mail')
    handler = logging.StreamHandler(strm=sys.stderr)
    logger.addHandler(handler)
    return logger


def main(args):
    options, args = options_parser.parse_args(args)
    
    lockfile = LockFile('/var/lock/launchpad-poimport.lock')
    lockfile.acquire()

    logger = create_logger()

    try:
        trans = initZopeless()
        execute_zcml_for_scripts(use_web_security=True)

        try:
            handleMail(trans)
        except ComponentLookupError, lookup_error:
            if lookup_error.args[0] == IMailBox:
                logger.error(
                    "No mail box is configured.\n\n"
                    "Please see mailbox.txt for info on how to configure one.")
            else:
                logger.warn(
                    "An exception occured in handleMail.", exc_info=True)
    finally:
        lockfile.release()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
