#!/usr/bin/python
# Copyright 2004 Canonical Ltd.  All rights reserved.


import canonical.lp, time
import sqlos.connection
import logging

from canonical.launchpad.database import ProductSet

class ImportDaemon:
    def __init__(self):
        self.setUp()

    def setUp(self):
        self._tm = canonical.lp.initZopeless()

    def commit(self):
        try:
            self._tm.commit()
        except:
            # We don't want to die, so we ignore any exception.
            logging.warning('We got an error committing the transaction',
                exc_info = 1)

    def nextImport(self):
        productSet = ProductSet()
        for product in productSet:
            for template in product.poTemplatesToImport():
                # We have a template with raw data to be imported.
                logging.info('Importing the template %s' % template.name)
                yield template
            for template in product.potemplates:
                for pofile in template.poFilesToImport():
                    # We have a po with raw data to be imported.
                    logging.info('Importing the %s translation of %s' % (
                        pofile.language.englishname, pofile.potemplate.name))
                    yield pofile

    def run(self):
        from canonical.database.sqlbase import SQLBase
        while True:
            found_any = False
            for object in self.nextImport():
                found_any = True
                # object could be a POTemplate or a POFile but both objects
                # implement the doRawImport method so we don't need to care
                # about it here.
                object.doRawImport()

                # As soon as the import is done, we commit the transaction so
                # it's not lost.
                self.commit()
            if not found_any:
                time.sleep(60)
                # XXX: force a rollback/begin pair here to reset the
                # transaction so we can see new pending imports.  There should
                # be a way to do this without mucking about with
                # SQLBase._connection, but calling self._tm.abort() doesn't
                # seem to work.
                #   -- Andrew Bennetts, 2004-12-16.
                SQLBase._connection.rollback()
                SQLBase._connection.begin()


if __name__ == '__main__':
    daemon = ImportDaemon()

    daemon.run()
