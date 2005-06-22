# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POFileSet', 'POFile']

import StringIO
from warnings import warn
import sets

# Zope interfaces
from zope.interface import implements
from zope.component import getUtility
from zope.exceptions import NotFoundError

# SQL imports
from sqlobject import (ForeignKey, IntCol, StringCol, BoolCol,
    SQLObjectNotFound)
from canonical.database.sqlbase import (SQLBase, flush_database_updates,
    sqlvalues)
from canonical.database.datetimecol import UtcDateTimeCol

# canonical imports
from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import (IPOFileSet, IEditPOFile,
    IPersonSet, IRawFileData, ITeam, IPOTemplateExporter,
    ZeroLengthPOExportError)
from canonical.launchpad.components.rosettastats import RosettaStats
from canonical.launchpad.components.pofile_adapters import POFileImporter
from canonical.launchpad.components.poparser import POParser, POHeader
from canonical.launchpad import helpers
from canonical.launchpad.database.pomsgid import POMsgID
from canonical.launchpad.database.potmsgset import POTMsgSet
from canonical.launchpad.database.pomsgset import POMsgSet
from canonical.launchpad.database.poselection import POSelection
from canonical.launchpad.database.posubmission import POSubmission
from canonical.librarian.interfaces import (ILibrarianClient, DownloadFailed,
    UploadFailed)
from canonical.lp.dbschema import (EnumCol, RosettaImportStatus,
    TranslationPermission)


class POFile(SQLBase, RosettaStats):
    implements(IEditPOFile, IRawFileData)

    _table = 'POFile'

    potemplate = ForeignKey(foreignKey='POTemplate',
                            dbName='potemplate',
                            notNull=True)
    language = ForeignKey(foreignKey='Language',
                          dbName='language',
                          notNull=True)
    description = StringCol(dbName='description',
                            notNull=False,
                            default=None)
    topcomment = StringCol(dbName='topcomment',
                           notNull=False,
                           default=None)
    header = StringCol(dbName='header',
                       notNull=False,
                       default=None)
    fuzzyheader = BoolCol(dbName='fuzzyheader',
                          notNull=True)
    lasttranslator = ForeignKey(foreignKey='Person',
                                dbName='lasttranslator',
                                notNull=False,
                                default=None)
    license = IntCol(dbName='license',
                     notNull=False,
                     default=None)
    currentcount = IntCol(dbName='currentcount',
                          notNull=True,
                          default=0)
    updatescount = IntCol(dbName='updatescount',
                          notNull=True,
                          default=0)
    rosettacount = IntCol(dbName='rosettacount',
                          notNull=True,
                          default=0)
    lastparsed = UtcDateTimeCol(dbName='lastparsed',
                                notNull=False,
                                default=None)
    owner = ForeignKey(foreignKey='Person',
                       dbName='owner',
                       notNull=True)
    pluralforms = IntCol(dbName='pluralforms',
                         notNull=True)
    variant = StringCol(dbName='variant',
                        notNull=False,
                        default=None)
    filename = StringCol(dbName='filename',
                         notNull=False,
                         default=None)
    exportfile = ForeignKey(foreignKey='LibraryFileAlias',
                            dbName='exportfile',
                            notNull=False,
                            default=None)
    exporttime = UtcDateTimeCol(dbName='exporttime',
                                notNull=False,
                                default=None)
    datecreated = UtcDateTimeCol(notNull=True,
        default=UTC_NOW)

    @property
    def title(self):
        """See IPOFile."""
        title = '%s translation of %s' % (
            self.language.displayname, self.potemplate.displayname)
        return title

    @property
    def translators(self):
        """See IPOFile."""
        translators = sets.Set()
        for group in self.potemplate.translationgroups:
            translator = group.query_translator(self.language)
            if translator is not None:
                translators.add(translator)
        return sorted(list(translators),
            key=lambda x: x.translator.name)

    @property
    def translationpermission(self):
        """See IPOFile."""
        return self.potemplate.translationpermission

    @property
    def contributors(self):
        """See IPOFile."""
        from canonical.launchpad.database.person import Person

        return Person.select("""
            POSubmission.person = Person.id AND
            POSubmission.pomsgset = POMsgSet.id AND
            POMsgSet.pofile = %d""" % self.id,
            clauseTables=('POSubmission', 'POMsgSet'),
            distinct=True)

    def canEditTranslations(self, person):
        """See IEditPOFile."""

        # If the person is None, then they cannot edit
        if person is None:
            return False

        # have a look at the aplicable permission policy
        tperm = self.translationpermission
        if tperm == TranslationPermission.OPEN:
            # if the translation policy is "open", then yes
            return True
        elif tperm == TranslationPermission.CLOSED:
            # if the translation policy is "closed", then check if the person is
            # in the set of translators
            # XXX sabdfl 25/05/05 this code could be improved when we have
            # implemented CrowdControl
            translators = [t.translator for t in self.translators]
            for translator in translators:
                if person.inTeam(translator):
                    return True
        else:
            raise NotImplementedError('Unknown permission %s' % tperm.name)

        # Finally, check for the owner of the PO file
        return person.inTeam(self.owner)

    def currentMessageSets(self):
        return POMsgSet.select(
            'POMsgSet.pofile = %d AND POMsgSet.sequence > 0' % self.id,
            orderBy='sequence')

    # XXX: Carlos Perello Marin 15/10/04: I don't think this method is needed,
    # it makes no sense to have such information or perhaps we should have it
    # as pot's len + the obsolete msgsets from this .po file.
    def __len__(self):
        """See IPOFile."""
        return self.translatedCount()

    def translated(self):
        """See IPOFile."""
        return iter(POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.iscomplete=TRUE AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0''' % self.id,
            clauseTables = ['POMsgSet']
            ))

    def untranslated(self):
        """See IPOFile."""
        raise NotImplementedError

    def __iter__(self):
        """See IPOFile."""
        return iter(self.currentMessageSets())

    def messageSet(self, key, onlyCurrent=False):
        """See IPOFile."""
        query = 'potemplate = %d' % self.potemplate.id
        if onlyCurrent:
            query += ' AND sequence > 0'

        if isinstance(key, slice):
            # XXX: Carlos Perello Marin 19/10/04: Not sure how to handle this.
            raise NotImplementedError
            #return POTMsgSet.select(query, orderBy='sequence')[key]

        if not isinstance(key, unicode):
            raise TypeError(
                "Can't index with type %s. (Must be slice or unicode.)"
                % type(key))

        # Find a message ID with the given text.
        try:
            messageID = POMsgID.byMsgid(key)
        except SQLObjectNotFound:
            raise NotFoundError(key)

        # Find a message set with the given message ID.

        result = POTMsgSet.selectOne(query +
            (' AND primemsgid = %d' % messageID.id))

        if result is None:
            raise NotFoundError(key)

        poresult = POMsgSet.selectOneBy(potmsgsetID=result.id, pofileID=self.id)
        if poresult is None:
            raise NotFoundError(key)
        return poresult

    def __getitem__(self, msgid_text):
        """See IPOFile."""
        return self.messageSet(msgid_text)

    def messageSetsNotInTemplate(self):
        """See IPOFile."""
        return iter(POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POMsgSet.sequence <> 0 AND
            POTMsgSet.sequence = 0''' % self.id,
            orderBy='sequence',
            clauseTables = ['POTMsgSet']))

    def getPOTMsgSetTranslated(self, slice=None):
        """See IPOFile."""
        # A POT set is translated only if the PO message set has
        # POMsgSet.iscomplete = TRUE.
        results = POTMsgSet.select('''
            POTMsgSet.potemplate = %s AND
            POTMsgSet.sequence > 0 AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POMsgSet.pofile = %s AND
            POMsgSet.isfuzzy = FALSE AND
            POMsgSet.iscomplete = TRUE
            ''' % sqlvalues(self.potemplate.id, self.id),
            clauseTables=['POMsgSet'],
            orderBy='POTMsgSet.sequence')

        if slice is None:
            for potmsgset in results:
                yield potmsgset
        else:
            for potmsgset in results[slice]:
                yield potmsgset

    def getPOTMsgSetUntranslated(self, slice=None):
        """See IPOFile."""
        # A POT set is not translated if the PO message set have
        # POMsgSet.iscomplete = FALSE or we don't have such POMsgSet or
        # POMsgSet.isfuzzy = TRUE.
        #
        # We are using raw queries because the LEFT JOIN.
        potmsgids = self._connection.queryAll('''
            SELECT POTMsgSet.id, POTMsgSet.sequence
            FROM POTMsgSet
            LEFT OUTER JOIN POMsgSet ON
                POTMsgSet.id = POMsgSet.potmsgset AND
                POMsgSet.pofile = %s
            WHERE
                (POMsgSet.isfuzzy = TRUE OR
                 POMsgSet.iscomplete = FALSE OR
                 POMsgSet.id IS NULL) AND
                 POTMsgSet.sequence > 0 AND
                 POTMsgSet.potemplate = %s
            ORDER BY POTMsgSet.sequence
            ''' % sqlvalues(self.id, self.potemplate.id))

        if slice is not None:
            # Want only a subset specified by slice.
            potmsgids = potmsgids[slice]

        ids = [str(L[0]) for L in potmsgids]

        if len(ids) > 0:
            # Get all POTMsgSet requested by the function using the ids that
            # we know are not 100% translated.
            # NOTE: This implementation put a hard limit on len(ids) == 9000
            # if we get more elements there we will get an exception. It
            # should not be a problem with our current usage of this method.
            results = POTMsgSet.select(
                'POTMsgSet.id IN (%s)' % ', '.join(ids),
            orderBy='POTMsgSet.sequence')

            for potmsgset in results:
                yield potmsgset

    def hasMessageID(self, messageID):
        """See IPOFile."""
        results = POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.primemsgid = %d''' % (self.id, messageID.id))
        return results.count() > 0

    def messageCount(self):
        """See IRosettaStats."""
        return self.potemplate.messageCount()

    def currentCount(self, language=None):
        """See IRosettaStats."""
        return self.currentcount

    def updatesCount(self, language=None):
        """See IRosettaStats."""
        return self.updatescount

    def rosettaCount(self, language=None):
        """See IRosettaStats."""
        return self.rosettacount

    # IEditPOFile
    def expireAllMessages(self):
        """See IEditPOFile."""
        for msgset in self.currentMessageSets():
            msgset.sequence = 0

    def updateStatistics(self, tested=False):
        """See IEditPOFile."""
        # make sure all the data is in the db
        flush_database_updates()
        # make a note of the pre-update position
        prior_current = self.currentcount
        prior_updates = self.updatescount
        prior_rosetta = self.rosettacount
        current = POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.sequence > 0 AND
            POMsgSet.publishedfuzzy = FALSE AND
            POMsgSet.publishedcomplete = TRUE AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0
            ''' % self.id, clauseTables=['POTMsgSet']).count()

        updates = POMsgSet.select('''
            POMsgSet.pofile = %s AND
            POMsgSet.sequence > 0 AND
            POMsgSet.isfuzzy = FALSE AND
            POMsgSet.iscomplete = TRUE AND
            POMsgSet.publishedfuzzy = FALSE AND
            POMsgSet.publishedcomplete = TRUE AND
            POMsgSet.isupdated = TRUE AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0
            ''' % sqlvalues(self.id),
            clauseTables=['POTMsgSet']).count()

        if tested:
            updates_from_first_principles = POMsgSet.select('''
                POMsgSet.pofile = %s AND
                POMsgSet.sequence > 0 AND
                POMsgSet.isfuzzy = FALSE AND
                POMsgSet.iscomplete = TRUE AND
                POMsgSet.publishedfuzzy = FALSE AND
                POMsgSet.publishedcomplete = TRUE AND
                POMsgSet.potmsgset = POTMsgSet.id AND
                POTMsgSet.sequence > 0 AND
                ActiveSubmission.id = POSelection.activesubmission AND
                PublishedSubmission.id = POSelection.publishedsubmission AND
                POSelection.pomsgset = POMsgSet.id AND
                ActiveSubmission.datecreated > PublishedSubmission.datecreated
                ''' % sqlvalues(self.id),
                clauseTables=['POSelection',
                              'POTMsgSet',
                              'POSubmission AS ActiveSubmission',
                              'POSubmission AS PublishedSubmission']).count()
            if updates != updates_from_first_principles:
                raise AssertionError('Failure in update statistics.')

        rosetta = POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.isfuzzy = FALSE AND
            POMsgSet.iscomplete = TRUE AND
            ( POMsgSet.sequence < 1 OR
              POMsgSet.publishedcomplete = FALSE OR
              POMsgSet.publishedfuzzy=TRUE ) AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0
            ''' % self.id,
            clauseTables=['POTMsgSet']).count()
        self.currentcount = current
        self.updatescount = updates
        self.rosettacount = rosetta
        return (current, updates, rosetta)

    def createMessageSetFromMessageSet(self, potmsgset):
        """See IEditPOFile."""
        messageSet = POMsgSet(
            sequence=0,
            pofile=self,
            iscomplete=False,
            publishedcomplete=False,
            obsolete=False,
            isfuzzy=False,
            publishedfuzzy=False,
            potmsgset=potmsgset)
        return messageSet

    def createMessageSetFromText(self, text):
        """See IEditPOFile."""
        try:
            potmsgset = self.potemplate[text]
        except KeyError:
            potmsgset = self.potemplate.createMessageSetFromText(text)

        return self.createMessageSetFromMessageSet(potmsgset)

    @property
    def latest_submission(self):
        """See IPOFile."""
        results = POSubmission.select('''
            POSubmission.pomsgset = POMsgSet.id AND
            POMsgSet.pofile = %s''' % sqlvalues(self.id),
            orderBy='-datecreated',
            clauseTables=['POMsgSet'])
        try:
            return results[0]
        except IndexError:
            return None


    # ICanAttachRawFileData implementation

    def attachRawFileData(self, contents, published, importer=None):
        """See ICanAttachRawFileData."""
        if self.variant:
            filename = '%s@%s.po' % (
                self.language.code, self.variant.encode('utf8'))
        else:
            filename = '%s.po' % self.language.code

        helpers.attachRawFileData(self, filename, contents, importer)

        self.rawfilepublished = published

    # IRawFileData implementation

    # Any use of this interface should adapt this object as an IRawFileData.

    rawfile = ForeignKey(foreignKey='LibraryFileAlias', dbName='rawfile',
                         notNull=False, default=None)
    rawimporter = ForeignKey(foreignKey='Person', dbName='rawimporter',
                             notNull=False, default=None)
    daterawimport = UtcDateTimeCol(dbName='daterawimport', notNull=False,
                                   default=None)
    rawimportstatus = EnumCol(dbName='rawimportstatus', notNull=True,
        schema=RosettaImportStatus, default=RosettaImportStatus.IGNORE)

    rawfilepublished = BoolCol(notNull=False, default=None)

    def doRawImport(self, logger=None):
        """See IRawFileData."""

        if self.rawfile is None:
            # We don't have anything to import.
            return

        rawdata = helpers.getRawFileData(self)

        # We need to parse the file to get the last translator information so
        # the translations are not assigned to the person who imports the
        # file.
        parser = POParser()

        try:
            parser.write(rawdata)
            parser.finish()
        except:
            # We should not get any exception here because we checked the file
            # before being imported, but this could help prevent programming
            # errors.
            self.rawimportstatus = RosettaImportStatus.FAILED
            return

        # Check now that the file we are trying to import is newer than the
        # one we already have in our database. That's done comparing the
        # PO-Revision-Date field of the headers.
        old_header = POHeader(msgstr = self.header)
        old_header.finish()

        # Get the old and new PO-Revision-Date entries as datetime objects.
        (old_date_string, old_date) = old_header.getPORevisionDate()
        (new_date_string, new_date) = parser.header.getPORevisionDate()

        # Check if the import should or not be ignored.
        if old_date is None or new_date is None:
            # One or both headers had a missing or wrong PO-Revision-Date, in
            # this case, the .po file is always imported but registering the
            # problem in the logs.
            if logger is not None:
                logger.warning(
                    'There is a problem with the dates importing %s language '
                    'for template %s. New: %s, old %s' % (
                    self.language.code,
                    self.potemplate.description,
                    new_date_string,
                    old_date_string))
        elif old_date >= new_date:
            # The new import is older or the same than the old import in the
            # system, the import is rejected and logged.
            if logger is not None:
                logger.warning(
                    'We got an older version importing %s language for'
                    ' template %s . New: %s, old: %s . Ignoring the import...'
                    % (self.language.code,
                       self.potemplate.description,
                       new_date_string,
                       old_date_string))
            self.rawimportstatus = RosettaImportStatus.FAILED
            return

        # By default the owner of the import is who imported it.
        default_owner = self.rawimporter

        try:
            last_translator = parser.header['Last-Translator']

            # XXX sabdfl 04/06/05 this looks like a standard email address:
            # would it not be better to use the Python email module to parse
            # this address?
            first_left_angle = last_translator.find("<")
            first_right_angle = last_translator.find(">")
            name = last_translator[:first_left_angle].replace(",","_")
            email = last_translator[first_left_angle+1:first_right_angle]
            name = name.strip()
            email = email.strip()
        except:
            # Usually we should only get a KeyError exception but if we get
            # any other exception we should do the same, use the importer name
            # as the person who owns the imported po file.
            person = default_owner
        else:
            # If we didn't got any error getting the Last-Translator field
            # from the pofile.
            if email == 'EMAIL@ADDRESS':
                # We don't have a real account, thus we just use the import
                # person as the owner.
                person = default_owner
            else:
                person = getUtility(IPersonSet).getByEmail(email)

                if person is None:
                    items = name.split()
                    if len(items) == 1:
                        givenname = name
                        familyname = ""
                    elif not items:
                        # No name, just an email
                        givenname = email.split("@")[0]
                        familyname = ""
                    else:
                        givenname = items[0]
                        familyname = " ".join(items[1:])

                    # We create a new user without a password.
                    try:
                        person = createPerson(email, name, givenname,
                                              familyname, password=None)
                    except:
                        # We had a problem creating the person...
                        person = None

                    if person is None:
                        # XXX: Carlos Perello Marin 20/12/2004 We have already
                        # that person in the database, we should get it instead
                        # of use the default one...
                        person = default_owner

        # we set "published" to the value of rawfilepublished and depend on
        # the enforcement that only editors can upload po files, so
        # is_editor will be True
        importer = POFileImporter(self, person, self.rawfilepublished, True)

        try:
            file = StringIO.StringIO(rawdata)

            importer.doImport(file)

            self.rawimportstatus = RosettaImportStatus.IMPORTED

            # We do not have to ask for a sqlobject sync before reusing the
            # data we just updated, because self.updateStatistics does that
            # for itself now.

            # Now we update the statistics after this new import
            self.updateStatistics()

        except:
            # The import failed, we mark it as failed so we could review it
            # later in case it's a bug in our code.
            self.rawimportstatus = RosettaImportStatus.FAILED
            if logger:
                logger.warning(
                    'We got an error importing %s language for %s template' % (
                        self.language.code, self.potemplate.title),
                        exc_info = 1)

    def validExportCache(self):
        """See IPOFile."""
        if self.exportfile is None:
            return False

        if self.exporttime == UTC_NOW:
            # XXX
            # This is a workaround for the fact that UTC_NOW can't be compared
            # against datetime values.
            # -- Dafydd Harries, 2005/06/21

            return True
        else:
            change_time = self.latest_submission.datecreated
            return change_time < self.exporttime

    def updateExportCache(self, contents):
        """See IPOFile."""
        client = getUtility(ILibrarianClient)

        if self.variant:
            filename = '%s@%s.po' % (
                self.language.code, self.variant.encode('UTF-8'))
        else:
            filename = '%s.po' % (self.language.code)

        size = len(contents)
        file = StringIO.StringIO(contents)

        # Note that UTC_NOW is resolved at the time at the beginning of the
        # transaction, rather than when the transaction is committed. This is
        # significant because translations could be added to the database
        # while the export transaction is in progress, and the export would
        # not include those translations.

        self.exportfile = client.addFile(filename, size, file,
            'appliction/x-po')
        self.exporttime = UTC_NOW

    def fetchExportCache(self):
        """Return the cached export file, if it exists, or None otherwise."""

        if self.exportfile is None:
            return None
        else:
            client = getUtility(ILibrarianClient)
            return client.getFileByAlias(self.exportfile).read()

    def uncachedExport(self):
        """Export this PO file without looking in the cache."""
        exporter = IPOTemplateExporter(self.potemplate)
        return exporter.export_pofile(self.language, self.variant)

    def export(self):
        """See IPOFile."""
        if self.validExportCache():
            return self.fetchExportCache()
        else:
            contents = self.uncachedExport()

            if len(contents) == 0:
                raise ZeroLengthPOExportError

            self.updateExportCache(contents)
            return contents

class POFileSet:
    implements(IPOFileSet)

    def getPOFilesPendingImport(self):
        """See IPOFileSet."""
        results = POFile.selectBy(rawimportstatus=RosettaImportStatus.PENDING)

        # XXX: Carlos Perello Marin 2005-03-24
        # Really ugly hack needed to do the initial import of the whole hoary
        # archive. It will disappear as soon as the whole
        # LaunchpadPackagePoAttach and LaunchpadPoImport are implemented so
        # rawfile is not used anymore and we start using Librarian.
        # The problem comes with the memory requirements to get more than 7500
        # rows into memory with about 200KB - 300KB of data each one.
        total = results.count()
        done = 0
        while done < total:
            for potemplate in results[done:done+100]:
                yield potemplate
            done = done + 100


