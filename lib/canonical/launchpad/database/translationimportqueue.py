# Copyright 2005 Canonical Ltd. All rights reserved.

__metaclass__ = type
__all__ = [
    'TranslationImportQueueEntry',
    'TranslationImportQueue'
    ]

import tarfile
import os.path
import datetime
from StringIO import StringIO
from zope.interface import implements
from zope.component import getUtility
from sqlobject import SQLObjectNotFound, StringCol, ForeignKey, BoolCol

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.launchpad.interfaces import (
    ITranslationImportQueueEntry, ITranslationImportQueue, IPOFileSet,
    IPOTemplateSet, ILanguageSet, NotFoundError)
from canonical.librarian.interfaces import ILibrarianClient
from canonical.lp.dbschema import RosettaImportStatus, EnumCol

# Number of days when the DELETED and IMPORTED entries are removed from the
# queue.
DAYS_TO_KEEP = 5

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
    is_published = BoolCol(dbName='is_published', notNull=True)
    pofile = ForeignKey(foreignKey='POFile', dbName='pofile',
        notNull=False, default=None)
    potemplate = ForeignKey(foreignKey='POTemplate',
        dbName='potemplate', notNull=False, default=None)
    status = EnumCol(dbName='status', notNull=True,
        schema=RosettaImportStatus, default=RosettaImportStatus.NEEDS_REVIEW)
    date_status_changed = UtcDateTimeCol(dbName='date_status_changed',
        notNull=True, default=DEFAULT)


    @property
    def sourcepackage(self):
        """See ITranslationImportQueueEntry."""
        from canonical.launchpad.database import SourcePackage

        if self.sourcepackagename is None or self.distrorelease is None:
            return None

        return SourcePackage(self.sourcepackagename, self.distrorelease)

    @property
    def guessed_potemplate(self):
        """See ITranslationImportQueueEntry."""
        assert self.path.endswith('.pot'), (
            "We cannot handle the file %s here." % self.path)

        # It's an IPOTemplate
        potemplate_set = getUtility(IPOTemplateSet)
        return potemplate_set.getPOTemplateByPathAndOrigin(
            self.path, productseries=self.productseries,
            distrorelease=self.distrorelease,
            sourcepackagename=self.sourcepackagename)

    @property
    def _guessed_pofile_from_path(self):
        """Return a POFile that we think it's related to this entry based on
        the path it's stored or None.
        """
        pofile_set = getUtility(IPOFileSet)
        return pofile_set.getPOFileByPathAndOrigin(
            self.path, productseries=self.productseries,
            distrorelease=self.distrorelease,
            sourcepackagename=self.sourcepackagename)

    @property
    def guessed_pofile(self):
        """See ITranslationImportQueueEntry."""
        assert self.path.endswith('.po'), (
            "We cannot handle the file %s here." % self.path)

        if self.potemplate is None:
            # We don't have the IPOTemplate object associated with this entry.
            # Try to guess it from the file path.
            return self._guessed_pofile_from_path

        # We know the IPOTemplate associated with this entry so we can try to
        # detect the right IPOFile.
        filename = os.path.basename(self.path)
        guessed_language, file_ext = filename.split(u'.', 1)
        if file_ext != 'po':
            # The filename does not follows the pattern 'LANGCODE.po'
            # so we cannot guess its language.
            # Fallback to the guessed value based on the path.
            return self._guessed_pofile_from_path

        if u'@' in guessed_language:
            # Seems like this entry is using a variant entry.
            language_code, language_variant = guessed_language.split(u'@')
        else:
            language_code = guessed_language
            language_variant = None

        language_set = getUtility(ILanguageSet)

        try:
            language = language_set[language_code]
        except NotFoundError:
            # We don't have such language in our database so we cannot
            # guess it using this method.
            # Fallback to the guessed value based on the path.
            return self._guessed_pofile_from_path

        if not language.visible:
            # The language is hidden by default, that would mean that
            # we got a bad import and that should be reviewed by
            # someone before importing. That's to prevent the import
            # of languages like 'es_ES' or 'fr_FR' instead of just
            # 'es' or 'fr'.
            # Fallback to the guessed value based on the path to accept
            # languages that the admin already accepted, even if by default
            # should not be accepted.
            return self._guessed_pofile_from_path

        # Get or create an IPOFile based on the info we guessed.
        return self.potemplate.getOrCreatePOFile(
            language_code, variant=language_variant, owner=self.importer)

    @property
    def import_into(self):
        """See ITranslationImportQueueEntry."""
        if self.pofile is not None:
            # The entry has an IPOFile associated where it should be imported.
            return self.pofile
        elif self.potemplate is not None and self.path.endswith('.pot'):
            # The entry has an IPOTemplate associated where it should be
            # imported.
            return self.potemplate
        else:
            # We don't know where this entry should be imported.
            return None

    def getFileContent(self):
        """See ITranslationImportQueueEntry."""
        client = getUtility(ILibrarianClient)
        return client.getFileByAlias(self.content.id).read()


class TranslationImportQueue:
    implements(ITranslationImportQueue)

    def __iter__(self):
        """See ITranslationImportQueue."""
        return iter(self.getAllEntries())

    def __getitem__(self, id):
        """See ITranslationImportQueue."""
        try:
            idnumber = int(id)
        except ValueError:
            raise NotFoundError(id)

        entry = self.get(idnumber)

        if entry is None:
            # The requested entry does not exist.
            raise NotFoundError(str(id))

        return entry

    def __len__(self):
        """See ITranslationImportQueue."""
        return TranslationImportQueueEntry.select().count()

    def iterNeedsReview(self):
        """See ITranslationImportQueue."""
        return iter(TranslationImportQueueEntry.selectBy(
            status=RosettaImportStatus.NEEDS_REVIEW,
            orderBy=['dateimported']))

    def addOrUpdateEntry(self, path, content, is_published, importer,
        sourcepackagename=None, distrorelease=None, productseries=None,
        potemplate=None):
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
            if potemplate is not None:
                 # Only set the linked IPOTemplate object if it's not None.
                 entry.potemplate = potemplate

            if (entry.status == RosettaImportStatus.DELETED or
                entry.status == RosettaImportStatus.FAILED):
                # We got an update for this entry. If the previous import is
                # deleted or failed we should retry the import now, just in
                # case it can be imported now.
                entry.status = RosettaImportStatus.NEEDS_REVIEW

            entry.date_status_changed = UTC_NOW
            entry.sync()
            return entry
        else:
            # It's a new row.
            entry = TranslationImportQueueEntry(path=path, content=alias,
                importer=importer, sourcepackagename=sourcepackagename,
                distrorelease=distrorelease, productseries=productseries,
                is_published=is_published, potemplate=potemplate)
            return entry

    def addOrUpdateEntriesFromTarball(self, content, is_published, importer,
        sourcepackagename=None, distrorelease=None, productseries=None,
        potemplate=None):
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
            productseries=productseries, potemplate=potemplate)

        return len(files)

    def get(self, id):
        """See ITranslationImportQueue."""
        try:
            return TranslationImportQueueEntry.get(id)
        except SQLObjectNotFound:
            return None

    def getAllEntries(self):
        """See ITranslationImportQueue."""
        return TranslationImportQueueEntry.select(
            orderBy=['status', 'dateimported'])

    def getFirstEntryToImport(self):
        """See ITranslationImportQueue."""
        return TranslationImportQueueEntry.selectFirstBy(
            status=RosettaImportStatus.APPROVED,
            orderBy=['dateimported'])

    def executeAutomaticReviews(self, ztm):
        """See ITranslationImportQueue."""
        there_are_entries_approved = False
        for entry in self.iterNeedsReview():
            if entry.import_into is None:
                # We don't have a place to import this entry. Try to guess it.
                if entry.path.endswith('.po'):
                    # Check if we can guess where it should be imported.
                    guessed = entry.guessed_pofile
                    if guessed is None:
                        # We were not able to guess a place to import it,
                        # leave the status of this entry as
                        # RosettaImportStatus.NEEDS_REVIEW and wait for an
                        # admin to manually review it.
                        continue
                    # Set the place where it should be imported.
                    entry.pofile = guessed

                else:
                    # It's a .pot file
                    # Check if we can guess where it should be imported.
                    guessed = entry.guessed_potemplate
                    if guessed is None:
                        # We were not able to guess a place to import it,
                        # leave the status of this entry as
                        # RosettaImportStatus.NEEDS_REVIEW and wait for an
                        # admin to manually review it.
                        continue
                    # Set the place where it should be imported.
                    entry.potemplate = guessed

            # Already know where it should be imported. The entry is approved
            # automatically.
            entry.status = RosettaImportStatus.APPROVED
            there_are_entries_approved = True
            # Do the commit to save the changes.
            ztm.commit()

        return there_are_entries_approved

    def cleanUpQueue(self):
        """See ITranslationImportQueue."""
        # Get DELETED and IMPORTED entries.
        delta = datetime.timedelta(DAYS_TO_KEEP)
        last_date = datetime.datetime.utcnow() - delta
        res = TranslationImportQueueEntry.select(
            "(status = %s OR status = %s) AND date_status_changed < %s" %
                sqlvalues(RosettaImportStatus.DELETED.value,
                          RosettaImportStatus.IMPORTED.value,
                          last_date))

        n_entries = res.count()

        # Delete the entries.
        for entry in res:
            self.remove(entry)

        return n_entries

    def remove(self, entry):
        """See ITranslationImportQueue."""
        TranslationImportQueueEntry.delete(entry.id)
