# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""This script is called from librarianformatter.txt to
demonstrate a script using the LibrarianFormatter
"""

__metaclass__ = type

import logging
from optparse import OptionParser
import sys

from canonical.launchpad.scripts import (
    execute_zcml_for_scripts,
    logger,
    logger_options,
    )


if __name__ == '__main__':
    parser = OptionParser()
    logger_options(parser)
    (options, args) = parser.parse_args()
    log = logger(options)
    # Test the root logger too, because some code is using it
    root_log = logging.getLogger()
    execute_zcml_for_scripts()
    print >> sys.stderr, 'Script Output'
    try:
        raise RuntimeError('Aargh')
    except RuntimeError:
        log.exception('Oops')
        root_log.exception('Root oops')

