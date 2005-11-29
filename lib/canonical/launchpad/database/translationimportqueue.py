# Copyright 2005 Canonical Ltd. All rights reserved.

__metaclass__ = type
__all__ = ['TranslationImportQueueEntry', 'TranslationImportQueue']

import tarfile
import os.path
from StringIO import StringIO
from zope.interface import implements
from zope.component import getUtility
from sqlobject import SQLObjectNotFound, StringCol, ForeignKey, BoolCol

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.constants import DEFAULT
from canonical.launchpad.interfaces import (
    ITranslationImportQueueEntry, ITranslationImportQueue, IPOFile,
    IPOFileSet, IPOTemplateSet, ICanAttachRawFileData, EntryFileNameError,
    NotFoundError, EntryBlocked)
from canonical.launchpad.database import SourcePackage
from canonical.librarian.interfaces import ILibrarianClient

class TranslationImportQueueEntry(SQLBase):
    implements(ITranslationImportQueueEntry)

    _table = 'TranslationImportQueueEntry'

    path = StringCol(dbName='path', notNull=True)
    content = ForeignKey(foreignKey='LibraryFileAlias', dbName='content',
        notNull=False)
    importer = ForeignKey(foreignKey='Person', dbName='importer',
        notNull=True)
    dateimported = UtcDateTimeCol(dbName='dateimported', notNull=True,
        default=DEFAULT)
    sourcepackagename = ForeignKey(foreignKey='SourcePackageName',
        dbName='sourcepackagename', notNull=False, default=None)
    distrorelease = ForeignKey(foreignKey='DistroRelease',
        dbName='distrorelease', notNull=False, default=None)
    productseries = ForeignKey(foreignKey='ProductSeries',
        dbName='productseries', notNull=False, default=None)
    is_blocked = BoolCol(dbName='is_blocked', notNull=True, default=False)
    is_published = BoolCol(dbName='is_published', notNull=True)
    pofile = ForeignKey(foreignKey='POFile', dbName='pofile',
        notNull=False, default=None)
    potemplate = ForeignKey(foreignKey='POTemplate',
        dbName='potemplate', notNull=False, default=None)

    @property
    def sourcepackage(self):
        """See ITranslationImportQueueEntry."""
        if self.sourcepackagename is None or self.distrorelease is None:
            return None

        return SourcePackage(self.sourcepackagename, self.distrorelease)

    @property
    def import_into(self):
        """See ITranslationImportQueueEntry."""
        # First check if a Rosetta Expert chose already where this file should
        # be attached
        if self.pofile is not None:
            return self.pofile
        if self.potemplate is not None:
            return self.potemplate

        # No information from admins, check to guess it from the path.
        if self.path.endswith('.pot'):
            # It's an IPOTemplate
            potemplate_set = getUtility(IPOTemplateSet)
            return potemplate_set.getPOTemplateByPathAndOrigin(
                self.path, productseries=self.productseries,
                distrorelease=self.distrorelease,
                sourcepackagename=self.sourcepackagename)
        elif self.path.endswith('.po'):
            # It's an IPOFile
            pofile_set = getUtility(IPOFileSet)
            return pofile_set.getPOFileByPathAndOrigin(
                self.path, productseries=self.productseries,
                distrorelease=self.distrorelease,
                sourcepackagename=self.sourcepackagename)
        else:
            # Unknow import so we don't know where to import it.
            return None

    def attachToPOFileOrPOTemplate(self, pofile_or_potemplate):
        """See ITranslationImportQueueEntry."""
        if self.is_blocked:
            raise EntryBlocked(
                'This entry cannot be imported. It has the is_blocked flag set')
        if IPOFile.providedBy(pofile_or_potemplate):
            if not self.path.lower().endswith('.po'):
                raise EntryFileNameError(
                    'The %s file cannot be imported as a PO file' % self.path)
            potemplate = pofile_or_potemplate.potemplate

        elif IPOTemplate.providedBy(pofile_or_potemplate):
            if not (self.path.lower().endswith('.po') or
                    self.path.lower().endswith('.pot')):
                raise EntryFileNameError(
                    'The %s file cannot be imported as a PO/POT file' %
                        self.path)
            potemplate = pofile_or_potemplate
        else:
            raise AssertionError(
                'Unknow object %s' % pofile_or_potemplate)
        if ((potemplate.distrorelease != self.distrorelease) or
            ((potemplate.sourcepackagename != self.sourcepackagename) and
             (potemplate.fromsourcepackagename != self.sourcepackagename)) or
            (potemplate.productseries != self.productseries)):
            # The given pofile is not for the same product/sourcepackage were
            # this file comes from.
            raise AssertionError(
                "The given pofile is not for this files'"
                " product/sourcepackage.")

        # Update the fields of the given object
        pofile_or_potemplate.path = self.path
        attach_object = ICanAttachRawFileData(pofile_or_potemplate)
        attach_object.attachRawFileDataAsFileAlias(
            self.content, self.is_published, self.importer, self.dateimported)

        # The import is noted now, so we should remove this entry from the
        # queue.
        TranslationImportQueueEntry.delete(self.id)

    def setBlocked(self, value=True):
        """See ITranslationImportQueueEntry."""
        self.is_blocked = value
        # Sync it so future queries get this change.
        self.sync()

    def getFileContent(self):
        """See ITranslationImportQueueEntry."""
        client = getUtility(ILibrarianClient)
        return client.getFileByAlias(self.content.id).read()


class TranslationImportQueue:
    implements(ITranslationImportQueue)

    def __iter__(self):
        """See ITranslationImportQueue."""
        return self.iterEntries(include_blocked=True)

    def __getitem__(self, id):
        """See ITranslationImportQueue."""
        try:
            idnumber = int(id)
        except ValueError:
            raise NotFoundError(id)

        return self.get(idnumber)

    def __len__(self):
        """See ITranslationImportQueue."""
        return TranslationImportQueueEntry.select().count()

    def addOrUpdateEntry(self, path, content, is_published, importer,
        sourcepackagename=None, distrorelease=None, productseries=None):
        """See ITranslationImportQueue."""
        if ((sourcepackagename is not None or distrorelease is not None) and
            productseries is not None):
            raise AssertionError(
                'The productseries argument cannot be not None if'
                ' sourcepackagename or distrorelease is also not None.')
        if (sourcepackagename is None and distrorelease is None and
            productseries is None):
            raise AssertionError('Any of sourcepackagename, distrorelease or'
                ' productseries must be not None.')

        if content is None or content == '':
            raise AssertionError('The content cannot be empty')

        if path is None or path == '':
            raise AssertionError('The path cannot be empty')

        # Upload the file into librarian.
        filename = os.path.basename(path)
        size = len(content)
        file = StringIO(content)
        client = getUtility(ILibrarianClient)
        alias = client.addFile(
            name=filename,
            size=size,
            file=file,
            contentType='application/x-po')

        # Check if we got already this request from this user.
        if sourcepackagename is not None:
            # The import is related with a sourcepackage and a distribution.
            entry = TranslationImportQueueEntry.selectOne(
                "TranslationImportQueueEntry.path = %s AND"
                " TranslationImportQueueEntry.importer = %s AND"
                " TranslationImportQueueEntry.sourcepackagename = %s AND"
                " TranslationImportQueueEntry.distrorelease = %s" % sqlvalues(
                    path, importer.id, sourcepackagename.id, distrorelease.id)
                )
        else:
            entry = TranslationImportQueueEntry.selectOne(
                "TranslationImportQueueEntry.path = %s AND"
                " TranslationImportQueueEntry.importer = %s AND"
                " TranslationImportQueueEntry.productseries = %s" % sqlvalues(
                    path, importer.id, productseries.id)
                )

        if entry is not None:
            # It's an update.
            entry.content = alias
            entry.is_published = is_published
            entry.sync()
            return entry
        else:
            # It's a new row.
            entry = TranslationImportQueueEntry(path=path, content=alias,
                importer=importer, sourcepackagename=sourcepackagename,
                distrorelease=distrorelease, productseries=productseries,
                is_published=is_published)
            return entry

    def addOrUpdateEntriesFromTarball(self, content, is_published, importer,
        sourcepackagename=None, distrorelease=None, productseries=None):
        """See ITranslationImportQueue."""

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

    def iterEntries(self, include_blocked=False):
        """See ITranslationImportQueue."""
        if include_blocked == True:
            res = TranslationImportQueueEntry.select()
        else:
            res = TranslationImportQueueEntry.select('is_blocked = FALSE')
        return res

    def iterEntriesForProductSeries(self, productseries):
        """See ITranslationImportQueue."""
        return TranslationImportQueueEntry.selectBy(productseriesID=productseries.id)

    def iterEntriesForDistroReleaseAndSourcePackageName(self, distrorelease,
        sourcepackagename):
        """See ITranslationImportQueue."""
        return TranslationImportQueueEntry.selectBy(
            distroreleaseID=distrorelease.id,
            sourcepackagenameID=sourcepackagename.id)

    def hasBlockedEntries(self):
        """See ITranslationImportQueue."""
        res = TranslationImportQueueEntry.select('is_blocked = TRUE')
        return res.count() > 0

    def iterBlockedEntries(self):
        """See ITranslationImportQueue."""
        return TranslationImportQueueEntry.select('is_blocked = TRUE')

    def get(self, id):
        """See ITranslationImportQueue."""
        try:
            return TranslationImportQueueEntry.get(id)
        except SQLObjectNotFound:
            raise NotFoundError(str(id))

    def remove(self, entry):
        """See ITranslationImportQueue."""
        TranslationImportQueueEntry.delete(entry.id)
