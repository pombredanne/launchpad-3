#!/usr/bin/python
# Copyright 2004 Canonical Ltd.  All rights reserved.


import canonical.lp, base64, time

import sqlos.connection
from StringIO import StringIO

from canonical.launchpad.database import POTemplate, ProjectSet
from canonical.lp.dbschema import RosettaImportStatus
from canonical.rosetta.pofile_adapters import TemplateImporter, POFileImporter


class ImportDaemon:
    def __init__(self):
        self._tm = canonical.lp.initZopeless()

    def commit(self):
        self._tm.commit()
        # XXX: Carlos Perello Marin 01/12/2004 This is used to clear the cache
        # so this script is useful, but it does not work.
        sqlos.connection.connCache.clear()

    def potimport(self, template):
        importer = TemplateImporter(template, template.rawimporter)

        # The importer needs a file-like object
        file = StringIO(base64.decodestring(template.rawfile))
    
        try:
            importer.doImport(file)
        except:
            # The import failed, we mark it as failed so we could review it
            # later in case it's a bug in our code.
            template.rawimportstatus = RosettaImportStatus.FAILED.value
        else:
            # We mark it as done.
            template.rawimportstatus = RosettaImportStatus.IMPORTED.value
            
        self.commit()

    def poimport(self, pofile):
        importer = POFileImporter(pofile, pofile.rawimporter)
    
        # The importer needs a file-like object
        file = StringIO(base64.decodestring(pofile.rawfile))
    
        try:
            importer.doImport(file)
        except:
            # The import failed, we mark it as failed so we could review it
            # later in case it's a bug in our code.
            pofile.rawimportstatus = RosettaImportStatus.FAILED.value
        else:
            # We mark it as done.
            pofile.rawimportstatus = RosettaImportStatus.IMPORTED.value

        self.commit()

    def nextImport(self):
        projectSet = ProjectSet()
        for project in projectSet:
            for product in project.products():
                for template in product.poTemplatesToImport():
                    # We have a template with raw data to be imported.
                    yield template
                for template in product.poTemplates():
                    for pofile in template.poFilesToImport():
                        # We have a po with raw data to be imported.
                        yield pofile

    def run(self):
        while True:
            for object in self.nextImport():
                if isinstance(object, POTemplate):
                    self.potimport(object)
                else:
                    self.poimport(object)
            else:
                time.sleep(60)

            
if __name__ == '__main__':
    daemon = ImportDaemon()

    daemon.run()
