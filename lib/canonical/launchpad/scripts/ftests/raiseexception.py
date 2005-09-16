# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""This script is called from librarianformatter.txt to
demonstrate a script using the LibrarianFormatter
"""

__metaclass__ = type

import sys
from canonical.launchpad.scripts import (
        logger, logger_options, execute_zcml_for_scripts
        )
from optparse import OptionParser

if __name__ == '__main__':
    parser = OptionParser()
    logger_options(parser)
    (options, args) = parser.parse_args()
    log = logger(options)
    execute_zcml_for_scripts()
    print >> sys.stderr, 'Script Output'
    try:
        raise RuntimeError('Aargh')
    except:
        log.exception('Oops')

