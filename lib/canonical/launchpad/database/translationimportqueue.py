# Copyright 2005 Canonical Ltd. All rights reserved.

__metaclass__ = type
__all__ = ['TranslationImportQueue', 'TranslationImportQueueSet']

from zope.exceptions import NotFoundError
from zope.interface import implements
from sqlobject import SQLObjectNotFound, StringCol, ForeignKey, BoolCol

from canonical.database.sqlbase import SQLBase
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.constants import DEFAULT
from canonical.launchpad.interfaces import (ITranslationImportQueue,
    ITranslationImportQueueSet)

class TranslationImportQueue(SQLBase):
    implements(ITranslationImportQueue)

    _table = 'TranslationImportQueue'

    path = StringCol(dbName='path', notNull=True)
    content = ForeignKey(foreignKey='LibraryFileAlias', dbName='content',
        notNull=False)
    importer = ForeignKey(foreignKey='Person', dbName='importer',
        notNull=True)
    dateimport = UtcDateTimeCol(dbName='dateimport', notNull=True,
        default=DEFAULT)
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='sourcepackagename', notNull=False, default=None)
    distrorelease = ForeignKey(foreignKey='DistroRelease',
        dbName='distrorelease', notNull=False, default=None)
    productseries = ForeignKey(foreignKey='ProductSeries',
        dbName='productseries', notNull=False, default=None)
    ignore = BoolCol(dbName='ignore', notNull=True, default=DEFAULT)
    ispublished = BoolCol(dbName='ispublished', notNull=True)


    def attachToPOFileOrPOTemplate(self, pofile_or_potemplate):
        """See ITranslationImportQueue."""
        if self.ignore:
            raise ValueError(
                'This entry cannot be imported. It has the ignore flag set')
        if IPOFile.providedBy(pofile_or_potemplate):
            if not self.path.lower().endswith('.po'):
                raise ValueError(
                    'The %s file cannot be imported as a PO file' % self.path)
            potemplate = pofile_or_potemplate.potemplate

        elif IPOTemplate.providedBy(pofile_or_potemplate):
            if not (self.path.lower().endswith('.po') or
                    self.path.lower().endswith('.pot')):
                raise ValueError(
                    'The %s file cannot be imported as a PO/POT file' %
                        self.path)
            potemplate = pofile_or_potemplate
        if ((potemplate.distrorelease is not None and
             self.distrorelease is not None and
             potemplate.distrorelease.id != self.distrorelease.id) or
            (potemplate.distrorelease is None and
             potemplate.distrorelease != self.distrorelease) or
            (potemplate.sourcepackagename is not None and
             self.sourcepackagename is not None and
             potemplate.sourcepackagename.id != self.sourcepackagename.id) or
            (potemplate.sourcepackagename is None and
             potemplate.sourcepackagename != self.sourcepackagename) or
            (potemplate.productseries is not None and
             self.productseries is not None and
             potemplate.productseries.id != self.productseries.id) or
            (potemplate.productseries is None and
             potemplate.productseries != self.productseries)):
            # The given pofile is not for the same product/sourcepackage were
            # this file comes from.
            raise ValueError('The given pofile is not for this files\''
                ' product/sourcepackage.')

        # Update the fields of the given object
        pofile_or_potemplate.path = self.path
        rawfile = IRawFileData(pofile_or_potemplate)
        rawfile.rawfile = self.content
        rawfile.daterawimport = self.dateimport
        rawfile.rawimporter = self.importer
        rawfile.rawimportstatus = RosettaImportStatus.PENDING

        # The import is noted now, so we should remove this entry from the
        # queue.
        TranslationImportQueue.delete(self.id)


class TranslationImportQueueSet:
    implements(ITranslationImportQueueSet)

    def __iter__(self):
        """See ITranslationImportQueueSet."""
        res = TranslationImportQueue.select()
        for entry in res:
            yield entry

    def addOrUpdateEntry(self, path, content, ispublished, importer,
        securesourcepackagepublishinghistory=None, productseries=None):
        """See ITranslationImportQueueSet."""
        if (securesourcepackagepublishinghistory is not None and
            productseries is not None):
            raise ValueError('The productseries argument cannot be not None'
                ' if securesourcepackagepublishinghistory is also not None.')
        if (securesourcepackagepublishinghistory is None and
            productseries is None):
            raise ValueError('Either securesourcepackagepublishinghistory or'
                ' productseries must be not None.')

        if content is None or content == '':
            raise ValueError('The content cannot be empty')

        if path is None or path == '':
            raise ValueError('The path cannot be empty')

        sourcepackagerelease = (
            securesourcepackagepublishinghistory.sourcepackagerelease
            )
        sourcepackagename = sourcepackagerelease.sourcepackagename
        distrorelease = securesourcepackagepublishinghistory.distrorelease

        res = TranslationImportQueue.selectBy(
            path=path, importer=importer, sourcepackagename=sourcepackagename,
            distrorelease=distrorelease, productseries=productseries)

        filename = path.split('/')[-1]
        size = len(content)
        file = StringIO(content)
        client = getUtility(ILibrarianClient)
        alias = client.addFile(
            name=filename,
            size=size,
            file=file,
            contentType='application/x-po')

        if res.count() > 0:
            # It's an update.
            entry = res[0]
            entry.content = alias
            entry.ispublished = ispublished
            entry.sync()
            return entry
        else:
            # It's a new row.
            entry = TranslationImportQueue(path=path, content=alias,
                importer=importer, sourcepackagename=sourcepackagename,
                distrorelease=distrorelease, productseries=productseries,
                ispublished=ispublished)
            return entry

    def getEntriesForProductSeries(self, productseries):
        """See ITranslationImportQueueSet."""
        res = TranslationImportQueue.selectBy(productseries=productseries)
        for entry in res:
            yield entry

    def getEntriesForDistroReleaseAndSourcePackageName(self, distrorelease,
        sourcepackagename):
        """See ITranslationImportQueueSet."""
        res = TranslationImportQueue.selectBy(
            distrorelease=distrorelease,
            sourcepackagename=sourcepackagename)
        for entry in res:
            yield entry

    def get(self, id):
        """See ITranslationImportQueueSet."""
        try:
            TranslationImportQueue.get(id)
        except SQLObjectNotFound:
            raise NotFoundError("Unable to locate an entry in the translation"
                " import queue with ID %s" % str(id))
