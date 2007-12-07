#!/usr/bin/python2.4
#
# Remove all translations from upstream. This script is useful to recover from
# breakages after importing bad .po files like the one reported at #32610
#
# Copyright 2006 Canonical Ltd.  All rights reserved.
#
import _pythonpath

import sys
import logging
from optparse import OptionParser
from zope.component import getUtility

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.lp import initZopeless
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.scripts.fix_plural_forms import (
    fix_plurals_in_all_pofiles)

logger_name = 'fix-pofile-plurals'

def parse_options(args):
    """Parse a set of command line options.

    Return an optparse.Values object.
    """
    parser = OptionParser()

    # Add the verbose/quiet options.
    logger_options(parser)

    (options, args) = parser.parse_args(args)

    return options

def main(argv):
    options = parse_options(argv[1:])
    logger_object = logger(options, logger_name)

    execute_zcml_for_scripts()
    ztm = initZopeless(dbuser=config.rosetta.rosettaadmin.dbuser)

    fix_plurals_in_all_pofiles(ztm, logger_object)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
