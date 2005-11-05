# Copyright 2005 Canonical Ltd. All rights reserved.

__metaclass__ = type
__all__ = ['TranslationImportQueue', 'TranslationImportQueueSet']

import tarfile
from StringIO import StringIO
from zope.interface import implements
from zope.component import getUtility
from sqlobject import SQLObjectNotFound, StringCol, ForeignKey, BoolCol

from canonical.database.sqlbase import SQLBase
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.constants import DEFAULT
from canonical.launchpad.interfaces import (ITranslationImportQueue,
    ITranslationImportQueueSet, NotFoundError, IPOFile, IPOFileSet,
    IPOTemplateSet)
from canonical.launchpad.database import SourcePackage
from canonical.librarian.interfaces import ILibrarianClient

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
    ignore = BoolCol(dbName='ignore', notNull=True, default=False)
    ispublished = BoolCol(dbName='ispublished', notNull=True)

    @property
    def sourcepackage(self):
        """See ITranslationImportQueue."""
        if self.sourcepackagename is None or self.distrorelease is None:
            return None

        return SourcePackage(self.sourcepackagename, self.distrorelease)

    @property
    def import_into(self):
        """See ITranslationImportQueue."""
        if self.path.endswith('.pot'):
            # It's an IPOTemplate
            potemplate_set = getUtility(IPOTemplateSet)
            try:
                return potemplate_set.getPOTemplateByPathAndOrigin(
                    self.path, productseries=self.productseries,
                    distrorelease=self.distrorelease,
                    sourcepackagename=self.sourcepackagename)
            except NotFoundError:
                return None
        elif self.path.endswith('.po'):
            # It's an IPOFile
            pofile_set = getUtility(IPOFileSet)
            try:
                return pofile_set.getPOFileByPathAndOrigin(
                    self.path, productseries=self.productseries,
                    distrorelease=self.distrorelease,
                    sourcepackagename=self.sourcepackagename)
            except NotFoundError:
                return None
        else:
            # Unknow import so we don't know where to import it.
            return None

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
        attach_object = ICanAttachRawFileData(pofile_or_potemplate)
        attach_object.attachRawFileDataAsFileAlias(
            file.content, file.ispublished, file.importer, file.dateimport)

        # The import is noted now, so we should remove this entry from the
        # queue.
        TranslationImportQueue.delete(self.id)


class TranslationImportQueueSet:
    implements(ITranslationImportQueueSet)

    def __iter__(self):
        """See ITranslationImportQueueSet."""
        for entry in self.getEntries(include_ignored=True):
            yield entry

    def addOrUpdateEntry(self, path, content, is_published, importer,
        sourcepackagename=None, distrorelease=None, productseries=None):
        """See ITranslationImportQueueSet."""
        if ((sourcepackagename is not None or distrorelease is not None) and
            productseries is not None):
            raise ValueError('The productseries argument cannot be not None'
                ' if sourcepackagename or distrorelease is also not None.')
        if (sourcepackagename is None and distrorelease is None and
            productseries is None):
            raise ValueError('Any of sourcepackagename, distrorelease or'
                ' productseries must be not None.')

        if content is None or content == '':
            raise ValueError('The content cannot be empty')

        if path is None or path == '':
            raise ValueError('The path cannot be empty')

        if sourcepackagename is not None:
            sourcepackagenameid = sourcepackagename.id
        else:
            sourcepackagenameid = None
        if distrorelease is not None:
            distroreleaseid = distrorelease.id
        else:
            distroreleaseid = None
        if productseries is not None:
            productseriesid = productseries.id
        else:
            productseriesid = None

        res = TranslationImportQueue.selectBy(
            path=path, importerID=importer.id,
            sourcepackagenameID=sourcepackagenameid,
            distroreleaseID=distroreleaseid,
            productseriesID=productseriesid)

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
            entry.ispublished = is_published
            entry.sync()
            return entry
        else:
            # It's a new row.
            entry = TranslationImportQueue(path=path, content=alias,
                importer=importer, sourcepackagename=sourcepackagename,
                distrorelease=distrorelease, productseries=productseries,
                ispublished=is_published)
            return entry

    def addOrUpdateEntriesFromTarball(self, content, is_published, importer,
        sourcepackagename=None, distrorelease=None, productseries=None):
        """See ITranslationImportQueueSet."""

        tarball = tarfile.open('', 'r', StringIO(content))
        names = tarball.getnames()

        files = [name
                 for name in names
                 if name.endswith('.pot') or name.endswith('.po')
                ]

        for file in files:
            content = tarball.extractfile(file).read()
            self.addOrUpdateEntry(file, content, is_published, importer,
            sourcepackagename=sourcepackagename, distrorelease=distrorelease,
            productseries=productseries)

        return len(files)

    def getEntries(self, include_ignored=False):
        """See ITranslationImportQueueSet."""
        if include_ignored == True:
            res = TranslationImportQueue.select()
        else:
            res = TranslationImportQueue.select('ignore = FALSE')
        for entry in res:
            yield entry

    def getEntriesForProductSeries(self, productseries):
        """See ITranslationImportQueueSet."""
        res = TranslationImportQueue.selectBy(productseriesID=productseries.id)
        for entry in res:
            yield entry

    def getEntriesForDistroReleaseAndSourcePackageName(self, distrorelease,
        sourcepackagename):
        """See ITranslationImportQueueSet."""
        res = TranslationImportQueue.selectBy(
            distroreleaseID=distrorelease.id,
            sourcepackagenameID=sourcepackagename.id)
        for entry in res:
            yield entry

    def get(self, id):
        """See ITranslationImportQueueSet."""
        try:
            TranslationImportQueue.get(id)
        except SQLObjectNotFound:
            raise NotFoundError("Unable to locate an entry in the translation"
                " import queue with ID %s" % str(id))
