#!/usr/bin/env python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Librarian garbage collector.

This script is run on the Librarian server to merge duplicate files,
remove expired files from the file system and clean up unreachable
rows in the database.

"""

__metaclass__ = type

import _pythonpath

from optparse import OptionParser

from canonical.launchpad.scripts import logger_options, logger
from canonical.librarian import librariangc
from canonical.lp import initZopeless
from canonical.config import config


def main():
    parser = OptionParser(description=__doc__)
    logger_options(parser)

    (options, args) = parser.parse_args()

    log = logger(options)
    librariangc.log = log

    ztm = initZopeless(dbuser=config.librarian.gc.dbuser, implicitBegin=False)

    librariangc.merge_duplicates(ztm)


if __name__ == '__main__':
    main()
