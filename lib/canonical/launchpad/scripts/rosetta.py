# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Functions used with the Rosetta PO import script."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces import IPOTemplateSet, IPOFileSet

class ImportProcess:
    """Import .po and .pot files attached to Rosetta."""

    def __init__(self, ztm, logger):
        """Initialize the ImportProcess object.

        Get two arguments, the Zope Transaction Manager and a logger for the
        warning/errors messages.
        """
        self.ztm = ztm
        self.logger = logger
        self.potemplateset = getUtility(IPOTemplateSet)
        self.pofileset = getUtility(IPOFileSet)

    def getPendingImports(self):
        """Iterate over all templates and PO files which are waiting to be
        imported.
        """

        for template in self.potemplateset.getTemplatesPendingImport():
            self.logger.info('Importing: %s' % template.title)
            yield template

        for pofile in self.pofileset.getPOFilesPendingImport():
            self.logger.info('Importing: %s' % pofile.title)
            yield pofile

    def run(self):
        for object in self.getPendingImports():
            # object could be a POTemplate or a POFile but both
            # objects implement the doRawImport method so we don't
            # need to care about it here.
            try:
                object.doRawImport(self.logger)
            except KeyboardInterrupt:
                self.ztm.abort()
                raise
            except:
                # If we have any exception, we log it and abort the
                # transaction.
                self.logger.error('Got an unexpected exception while'
                                  ' importing %s' % object.title, exc_info=1)
                self.ztm.abort()
                continue

            # As soon as the import is done, we commit the transaction
            # so it's not lost.
            try:
                self.ztm.commit()
            except KeyboardInterrupt:
                self.ztm.abort()
                raise
            except:
                # If we have any exception, we log it and abort the
                # transaction.
                self.logger.error('We got an unexpected exception while'
                                  ' committing the transaction', exc_info=1)
                self.ztm.abort()
