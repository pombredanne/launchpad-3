#!/usr/bin/python
# Copyright 2004 Canonical Ltd.  All rights reserved.


import canonical.lp, time
import sqlos.connection

from canonical.launchpad.database import ProductSet

class ImportDaemon:
    def setUp(self):
        self._tm = canonical.lp.initZopeless()

    def commit(self):
        self._tm.commit()

    def nextImport(self):
        # We create the connection every time to prevent a problem with cached
        # data that don't let the daemon to see changes done from launchpad.
        self.setUp()
        productSet = ProductSet()
        for product in productSet:
            for template in product.poTemplatesToImport():
                # We have a template with raw data to be imported.
                yield template
            for template in product.potemplates:
                for pofile in template.poFilesToImport():
                    # We have a po with raw data to be imported.
                    yield pofile

    def run(self):
        while True:
            for object in self.nextImport():
                # object could be a POTemplate or a POFile but both objects
                # implement the doRawImport method so we don't need to care
                # about it here.
                object.doRawImport()

                # As soon as the import is done, we commit the transaction so
                # it's not lost.
                self.commit()
            else:
                time.sleep(60)

            
if __name__ == '__main__':
    daemon = ImportDaemon()

    daemon.run()
