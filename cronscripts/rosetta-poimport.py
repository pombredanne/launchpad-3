#!/usr/bin/env python
# Copyright 2004 Canonical Ltd.  All rights reserved.

import logging, sys

from optparse import OptionParser

from canonical.lp import initZopeless
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.database import ProductSet

_default_lock_file = '/var/lock/launchpad-poimport.lock'

class ImportProcess:
    def __init__(self):
        self._tm = initZopeless()
        self.productSet = ProductSet()

    def commit(self):
        self._tm.commit()

    def abort(self):
        self._tm.abort()

    def nextImport(self):
        for product in self.productSet:
            for template in product.poTemplatesToImport():
                # We have a template with raw data to be imported.
                logger.info('Importing the template %s from %s' % (
                    template.name, product.displayname))
                yield template
            for template in product.potemplates:
                for pofile in template.poFilesToImport():
                    # We have a po with raw data to be imported.
                    logger.info('Importing the %s translation of %s from %s' % (
                        pofile.language.englishname,
                        template.name,
                        product.displayname))
                    yield pofile

    def run(self):
        try:
            for object in self.nextImport():
                # object could be a POTemplate or a POFile but both
                # objects implement the doRawImport method so we don't
                # need to care about it here.
                object.doRawImport(logger)

                # As soon as the import is done, we commit the transaction
                # so it's not lost.
                self.commit()
        except:
            # If we have any exception, we log it before terminating the
            # process.
            logger.error('We got an unexpected exception', exc_info = 1)
            self.abort()

def parse_options():
    parser = OptionParser()
    parser.add_option("-v", "--verbose", dest="verbose",
        default=0, action="count",
        help="Displays extra information.")
    parser.add_option("-q", "--quiet", dest="quiet",
        default=0, action="count",
        help="Display less information.")
    parser.add_option("-l", "--lockfile", dest="lockfilename",
        default=_default_lock_file,
        help="The file the script should use to lock the process.")

    (options, args) = parser.parse_args()

    return options


def main():
    # Do the import of all pending files from the queue.
    process = ImportProcess()
    logger.debug('Starting the import process')
    process.run()
    logger.debug('Finished the import process')


def setUpLogger():
    loglevel = logging.WARN

    for i in range(options.verbose):
        if loglevel == logging.INFO:
            loglevel = logging.DEBUG
        elif loglevel == logging.WARN:
            loglevel = logging.INFO
    for i in range(options.quiet):
        if loglevel == logging.WARN:
            loglevel = logging.ERROR
        elif loglevel == logging.ERROR:
            loglevel = logging.CRITICAL

    hdlr = logging.StreamHandler(strm=sys.stderr)
    hdlr.setFormatter(logging.Formatter(
        fmt='%(asctime)s %(levelname)s %(message)s'
        ))
    logger.addHandler(hdlr)
    logger.setLevel(loglevel)


if __name__ == '__main__':

    options = parse_options()

    # Get the global logger for this task.
    logger = logging.getLogger("poimport")
    # customized the logger output.
    setUpLogger()

    # Create a lock file so we don't have two daemons running at the same time.
    lockfile = LockFile(options.lockfilename, logger=logger)
    try:
        lockfile.acquire()
    except OSError:
        logger.info("lockfile %s already exists, exiting",
                    options.lockfilename)
        sys.exit(0)

    try:
        main()
    finally:
        # Release the lock so next planned task can be executed.
        lockfile.release()

