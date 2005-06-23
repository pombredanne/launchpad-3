#!/usr/bin/env python
# Copyright 2004 Canonical Ltd.  All rights reserved.

import logging, sys

from optparse import OptionParser

from canonical.lp import initZopeless
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.scripts.rosetta import create_logger, \
    calculate_loglevel
from canonical.launchpad.database import POTemplateSet, POFileSet

_default_lock_file = '/var/lock/launchpad-poimport.lock'

class ImportProcess:
    def __init__(self):
        self._tm = initZopeless()
        self.po_templates = POTemplateSet()
        self.po_files = POFileSet()

    def commit(self):
        self._tm.commit()

    def abort(self):
        self._tm.abort()

    def getPendingImports(self):
        '''Iterate over all PO templates and PO files which are waiting to be
        imported.
        '''

        for template in self.po_templates.getTemplatesPendingImport():
            logger.info('Importing the template: %s' % template.title)
            yield template

        for pofile in self.po_files.getPOFilesPendingImport():
            logger.info('Importing the %s translation of %s' % (
                pofile.language.englishname, pofile.potemplate.title))
            yield pofile

    def run(self):
        for object in self.getPendingImports():
            # object could be a POTemplate or a POFile but both
            # objects implement the doRawImport method so we don't
            # need to care about it here.
            try:
                object.doRawImport(logger)
            except KeyboardInterrupt:
                self.abort()
                raise
            except:
                # If we have any exception, we log it before terminating
                # the process.
                logger.error('We got an unexpected exception while importing',
                             exc_info = 1)
                self.abort()
                continue

            # As soon as the import is done, we commit the transaction
            # so it's not lost.
            try:
                self.commit()
            except KeyboardInterrupt:
                self.abort()
                raise
            except:
                # If we have any exception, we log it before terminating
                # the process.
                logger.error('We got an unexpected exception while committing'
                             'the transaction', exc_info = 1)
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

if __name__ == '__main__':
    execute_zcml_for_scripts()

    options = parse_options()

    # Get the global logger for this task.
    loglevel = calculate_loglevel(options.quiet, options.verbose)
    logger = create_logger('poimport', loglevel)

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

