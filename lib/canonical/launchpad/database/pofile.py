# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POFileSet', 'POFile']

import StringIO
import base64

# Zope interfaces
from zope.interface import implements
from zope.component import getUtility

# SQL imports
from sqlobject import \
    DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, flush_database_updates

# canonical imports
from canonical.launchpad.interfaces import \
    IPOFileSet, IEditPOFile, IPersonSet, IRawFileData
from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import RosettaImportStatus
from canonical.launchpad.components.rosettastats import RosettaStats
from canonical.launchpad.components.pofile_adapters import POFileImporter
from canonical.launchpad.components.poparser import POParser, POHeader
from canonical.launchpad import helpers
from canonical.launchpad.database.pomsgid import POMsgID
from canonical.launchpad.database.potmsgset import POTMsgSet
from canonical.launchpad.database.pomsgset import POMsgSet
from canonical.launchpad.database.potranslationsighting import \
    POTranslationSighting


class POFile(SQLBase, RosettaStats):
    implements(IEditPOFile, IRawFileData)

    _table = 'POFile'

    potemplate = ForeignKey(foreignKey='POTemplate',
                            dbName='potemplate',
                            notNull=True)
    language = ForeignKey(foreignKey='Language',
                          dbName='language',
                          notNull=True)
    title = StringCol(dbName='title',
                      notNull=False,
                      default=None)
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
    lastparsed = DateTimeCol(dbName='lastparsed',
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


    def currentMessageSets(self):
        return POMsgSet.select(
            'POMsgSet.pofile = %d AND POMsgSet.sequence > 0' % self.id,
            orderBy='sequence')

    # XXX: Carlos Perello Marin 15/10/04: I don't think this method is needed,
    # it makes no sense to have such information or perhaps we should have it
    # as pot's len + the obsolete msgsets from this .po file.
    def __len__(self):
        return self.translatedCount()

    def translated(self):
        return iter(POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.iscomplete=TRUE AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0''' % self.id,
            clauseTables = ['POMsgSet']
            ))

    def untranslated(self):
        '''XXX'''
        raise NotImplementedError

    def __iter__(self):
        return iter(self.currentMessageSets())

    def messageSet(self, key, onlyCurrent=False):
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
            raise KeyError, key

        # Find a message set with the given message ID.

        result = POTMsgSet.selectOne(query +
            (' AND primemsgid = %d' % messageID.id))

        if result is None:
            raise KeyError, key

        poresult = POMsgSet.selectOneBy(potmsgsetID=result.id, pofileID=self.id)
        if poresult is None:
            raise KeyError, key
        return poresult

    def __getitem__(self, msgid_text):
        return self.messageSet(msgid_text)

    def messageSetsNotInTemplate(self):
        return iter(POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POMsgSet.sequence <> 0 AND
            POTMsgSet.sequence = 0''' % self.id,
            orderBy='sequence',
            clauseTables = ['POTMsgSet']))

    def hasMessageID(self, messageID):
        results = POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.primemsgid = %d''' % (self.id, messageID.id))
        return results.count() > 0

    def messageCount(self):
        return self.potemplate.messageCount()

    def currentCount(self, language=None):
        return self.currentcount

    def updatesCount(self, language=None):
        return self.updatescount

    def rosettaCount(self, language=None):
        return self.rosettacount

    def getContributors(self):
        return getUtility(IPersonSet).getContributorsForPOFile(self)

    # IEditPOFile
    def expireAllMessages(self):
        for msgset in self.currentMessageSets():
            msgset.sequence = 0

    def updateStatistics(self, newImport=False):
        if newImport:
            # The current value should change only with a new import, if not,
            # it will be always the same.
            current = POMsgSet.select('''
                POMsgSet.pofile = %d AND
                POMsgSet.sequence > 0 AND
                POMsgSet.fuzzy = FALSE AND
                POMsgSet.iscomplete = TRUE AND
                POMsgSet.potmsgset = POTMsgSet.id AND
                POTMsgSet.sequence > 0
            ''' % self.id, clauseTables=['POTMsgSet']).count()
        else:
            current = self.currentcount

        # XXX: Carlos Perello Marin 27/10/04: We should fix the schema if we
        # want that updates/rosetta is correctly calculated, if we have fuzzy
        # msgset and then we fix it from Rosetta it will be counted as an
        # update when it's not.
        updates = POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.sequence > 0 AND
            POMsgSet.fuzzy = FALSE AND
            POMsgSet.iscomplete = TRUE AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0 AND
            EXISTS (SELECT *
                    FROM
                        POTranslationSighting FileSight,
                        POTranslationSighting RosettaSight
                    WHERE
                        FileSight.pomsgset = POMsgSet.id AND
                        RosettaSight.pomsgset = POMsgSet.id AND
                        FileSight.pluralform = RosettaSight.pluralform AND
                        FileSight.inLastRevision = TRUE AND
                        RosettaSight.inLastRevision = FALSE AND
                        FileSight.active = FALSE AND
                        RosettaSight.active = TRUE )
            ''' % self.id, clauseTables=['POTMsgSet']).count()

        rosetta = POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.fuzzy = FALSE AND
            POMsgSet.iscomplete = TRUE AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0 AND
            NOT EXISTS (
                SELECT *
                FROM
                    POTranslationSighting FileSight
                WHERE
                    FileSight.pomsgset = POMsgSet.id AND
                    FileSight.inLastRevision = TRUE) AND
            EXISTS (
                SELECT *
                FROM
                    POTranslationSighting RosettaSight
                WHERE
                    RosettaSight.pomsgset = POMsgSet.id AND
                    RosettaSight.inlastrevision = FALSE AND
                    RosettaSight.active = TRUE)
            ''' % self.id,
            clauseTables=['POTMsgSet']).count()
        self.set(currentcount=current,
                 updatescount=updates,
                 rosettacount=rosetta)
        return (current, updates, rosetta)

    def createMessageSetFromMessageSet(self, potmsgset):
        """Creates in the database a new message set.

        Returns that message set.
        """
        messageSet = POMsgSet(
            sequence=0,
            pofile=self,
            iscomplete=False,
            obsolete=False,
            fuzzy=False,
            potmsgset=potmsgset)

        return messageSet

    def createMessageSetFromText(self, text):
        try:
            potmsgset = self.potemplate[text]
        except KeyError:
            potmsgset = self.potemplate.createMessageSetFromText(text)

        return self.createMessageSetFromMessageSet(potmsgset)

    def latest_sighting(self):
        '''
        SELECT * FROM POTranslationSighting WHERE POTranslationSighting.id =
        POMsgSet.id AND POMsgSet.pofile = 2 ORDER BY datelastactive;
        '''
        sightings = POTranslationSighting.select('''
            POTranslationSighting.pomsgset = POMsgSet.id AND
            POMsgSet.pofile = %d''' % self.id,
            orderBy='-datelastactive',
            clauseTables=['POMsgSet'])
        try:
            return sightings[0]
        except IndexError:
            return None
    latest_sighting = property(latest_sighting)

    # ICanAttachRawFileData implementation

    def attachRawFileData(self, contents, importer=None):
        """See ICanAttachRawFileData."""
        helpers.attachRawFileData(self, contents, importer)

    # IRawFileData implementation

    # Any use of this interface should adapt this object as an IRawFileData.

    rawfile = StringCol(dbName='rawfile', notNull=False, default=None)
    rawimporter = ForeignKey(foreignKey='Person', dbName='rawimporter',
                             notNull=False, default=None)
    daterawimport = DateTimeCol(dbName='daterawimport', notNull=False,
                                default=None)
    rawimportstatus = EnumCol(dbName='rawimportstatus', notNull=True,
        schema=RosettaImportStatus, default=RosettaImportStatus.IGNORE)

    def doRawImport(self, logger=None):
        """See IRawFileData."""

        if self.rawfile is None:
            # We don't have anything to import.
            return

        rawdata = base64.decodestring(self.rawfile)

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
                # This import is here to prevent circular dependencies.
                from canonical.launchpad.database.person import \
                    PersonSet, createPerson

                person_set = PersonSet()

                person = person_set.getByEmail(email)

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

        importer = POFileImporter(self, person)

        try:
            file = StringIO.StringIO(rawdata)

            importer.doImport(file)

            self.rawimportstatus = RosettaImportStatus.IMPORTED

            # Ask for a sqlobject sync before reusing the data we just
            # updated.
            flush_database_updates()

            # Now we update the statistics after this new import
            self.updateStatistics(newImport=True)

        except:
            # The import failed, we mark it as failed so we could review it
            # later in case it's a bug in our code.
            self.rawimportstatus = RosettaImportStatus.FAILED
            if logger:
                logger.warning(
                    'We got an error importing %s language for %s template' % (
                        self.language.code, self.potemplate.title),
                        exc_info = 1)


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


