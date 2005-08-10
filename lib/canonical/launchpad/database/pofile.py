# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POFile', 'DummyPOFile', 'POFileSet']

import StringIO
import pytz
import datetime
import os.path

# Zope interfaces
from zope.interface import implements, providedBy
from zope.component import getUtility
from zope.exceptions import NotFoundError
from zope.event import notify

from sqlobject import (ForeignKey, IntCol, StringCol, BoolCol,
    SQLObjectNotFound)

from canonical.database.sqlbase import (SQLBase, flush_database_updates,
    sqlvalues)
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.constants import UTC_NOW

from canonical.lp.dbschema import (EnumCol, RosettaImportStatus,
    TranslationPermission, TranslationValidationStatus)

import canonical.launchpad
from canonical.launchpad import helpers
from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.interfaces import (IPOFileSet, IEditPOFile,
    IRawFileData, IPOTemplateExporter, ZeroLengthPOExportError,
    ILibraryFileAliasSet, IPOFile, ILaunchpadCelebrities)

from canonical.launchpad.database.pomsgid import POMsgID
from canonical.launchpad.database.potmsgset import POTMsgSet
from canonical.launchpad.database.pomsgset import POMsgSet

from canonical.launchpad.components.rosettastats import RosettaStats
from canonical.launchpad.components.poimport import import_po, OldPOImported
from canonical.launchpad.components.poparser import (POSyntaxError,
    POHeader, POInvalidInputError)
from canonical.launchpad.event.sqlobjectevent import SQLObjectModifiedEvent

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

    latestsubmission = ForeignKey(foreignKey='POSubmission',
        dbName='latestsubmission', notNull=False, default=None)

    @property
    def title(self):
        """See IPOFile."""
        title = '%s translation of %s' % (
            self.language.displayname, self.potemplate.displayname)
        return title

    @property
    def translators(self):
        """See IPOFile."""
        translators = set()
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

        rosetta_experts = getUtility(ILaunchpadCelebrities).rosetta_expert

        if person.inTeam(rosetta_experts):
            # Rosetta experts can edit translations always.
            return True

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

        if slice is not None:
            results = results[slice]

        for potmsgset in results:
            yield potmsgset

    def getPOTMsgSetFuzzy(self, slice=None):
        """See IPOFile."""
        results = POTMsgSet.select('''
            POTMsgSet.potemplate = %s AND
            POTMsgSet.sequence > 0 AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POMsgSet.pofile = %s AND
            POMsgSet.isfuzzy = TRUE
            ''' % sqlvalues(self.potemplate.id, self.id),
            clauseTables=['POMsgSet'],
            orderBy='POTmsgSet.sequence')

        if slice is not None:
            results = results[slice]

        for potmsgset in results:
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

    def getPOTMsgSetWithErrors(self, slice=None):
        """See IPOFile."""
        results = POTMsgSet.select('''
            POTMsgSet.potemplate = %s AND
            POTMsgSet.sequence > 0 AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POMsgSet.pofile = %s AND
            POSelection.pomsgset = POMsgSet.id AND
            POSelection.publishedsubmission = POSubmission.id AND
            POSubmission.pluralform = 0 AND
            POSubmission.validationstatus <> %s
            ''' % sqlvalues(self.potemplate.id, self.id,
                            TranslationValidationStatus.OK),
            clauseTables=['POMsgSet', 'POSelection', 'POSubmission'],
            orderBy='POTmsgSet.sequence')

        if slice is not None:
            results = results[slice]

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

    def updateHeader(self, new_header):
        """See IEditPOFile."""
        # check that the plural forms info is valid
        new_plural_form = new_header.get('Plural-Forms', None)
        if new_plural_form is None:
            # The new header does not have plural form information.
            # Parse the old header.
            old_header = POHeader(msgstr=self.header)
            # The POHeader needs to know is ready to be used.
            old_header.finish()
            old_plural_form = old_header.get('Plural-Forms', None)
            if old_plural_form is not None:
                # First attempt: use the plural-forms header that is already
                # in the database, if it exists.
                new_header['Plural-Forms'] = old_header['Plural-Forms']
            elif self.language.pluralforms is not None:
                # Second attempt: get the default value for plural-forms from
                # the language table.
                new_header['Plural-Forms'] = self.language.pluralforms
            else:
                # we absolutely don't know it; only complain if
                # a plural translation is present
                # XXX Carlos Perello Marin 2005-06-15: We should implement:
                # https://launchpad.ubuntu.com/malone/bugs/1186 instead of
                # set it to this default value...
                new_header['Plural-Forms'] = 1
        # XXX sabdfl 27/05/05 should we also differentiate between
        # washeaderfuzzy and isheaderfuzzy?
        self.topcomment = new_header.commentText
        self.header = new_header.msgstr
        self.fuzzyheader = 'fuzzy' in new_header.flags
        self.pluralforms = new_header.nplurals

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

    def isPORevisionDateNewer(self, header):
        """See IPOFile."""
        # Check now that the file we are trying to import is newer than the
        # one we already have in our database. That's done comparing the
        # PO-Revision-Date field of the headers.
        old_header = POHeader(msgstr=self.header)
        old_header.finish()

        # Get the old and new PO-Revision-Date entries as datetime objects.
        (old_date_string, old_date) = old_header.getPORevisionDate()
        (new_date_string, new_date) = header.getPORevisionDate()

        # Check if the import should or not be ignored.
        if old_date is None or new_date is None or old_date < new_date:
            # If one or both headers had a missing or wrong PO-Revision-Date,
            # the new header is always accepted as newer.
            return True
        elif old_date >= new_date:
            return False

    def doRawImport(self, logger=None):
        """See IRawFileData."""
        rawdata = helpers.getRawFileData(self)

        file = StringIO.StringIO(rawdata)

        # Store the object status before the changes.
        object_before_modification = helpers.Snapshot(
            self, providing=providedBy(self))

        try:
            errors = import_po(self, file, self.rawfilepublished)
        except (POSyntaxError, POInvalidInputError):
            # The import failed, we mark it as failed so we could review it
            # later in case it's a bug in our code.
            # XXX Carlos Perello Marin 2005-06-22: We should intregrate this
            # kind of error with the new TranslationValidation feature.
            self.rawimportstatus = RosettaImportStatus.FAILED
            if logger:
                logger.warning(
                    'Error importing %s' % self.title, exc_info=1)
            return
        except OldPOImported:
            # The attached file is older than the last imported one, we ignore
            # it.
            self.rawimportstatus = RosettaImportStatus.IGNORE
            if logger:
                logger.warning('Got an old version for %s' % self.title)
            return

        # Request a sync of 'self' as we need to use real datetime values.
        self.sync()

        # Prepare the mail notification.

        msgsets_imported = POMsgSet.select(
            'sequence > 0 AND pofile=%s' % (sqlvalues(self.id))).count()

        UTC = pytz.timezone('UTC')
        # XXX: Carlos Perello Marin 2005-06-29 This code should be using the
        # solution defined by PresentingLengthsOfTime spec when it's
        # implemented.
        elapsedtime = datetime.datetime.now(UTC) - self.daterawimport
        elapsedtime_text = ''
        hours = elapsedtime.seconds / 3600
        minutes = (elapsedtime.seconds % 3600) / 60
        if elapsedtime.days > 0:
            elapsedtime_text += '%d days ' % elapsedtime.days
        if hours > 0:
            elapsedtime_text += '%d hours ' % hours
        if minutes > 0:
            elapsedtime_text += '%d minutes ' % minutes

        if len(elapsedtime_text) > 0:
            elapsedtime_text += 'ago'
        else:
            elapsedtime_text = 'just requested'

        replacements = {
            'importer': self.rawimporter.displayname,
            'dateimport': self.daterawimport.strftime('%F %R%z'),
            'elapsedtime': elapsedtime_text,
            'numberofmessages': msgsets_imported,
            'language': self.language.displayname,
            'template': self.potemplate.displayname
            }

        if len(errors):
            # There were errors.
            errorsdetails = ''
            for error in errors:
                pomsgset = error['pomsgset']
                pomessage = error['pomessage']
                error_message = error['error-message']
                errorsdetails = errorsdetails + '%d.  [msg %d]\n"%s":\n\n%s\n\n' % (
                    pomsgset.potmsgset.sequence,
                    pomsgset.sequence,
                    error_message,
                    unicode(pomessage))

            replacements['numberoferrors'] = len(errors)
            replacements['errorsdetails'] = errorsdetails
            replacements['numberofcorrectmessages'] = (msgsets_imported -
                len(errors))

            template_mail = 'poimport-error.txt'
            subject = 'Translation problems - %s - %s' % (
                self.language.displayname, self.potemplate.displayname)
        else:
            template_mail = 'poimport-confirmation.txt'
            subject = 'Translation import - %s - %s' % (
                self.language.displayname, self.potemplate.displayname)

        # Send the email.
        template_file = os.path.join(
            os.path.dirname(canonical.launchpad.__file__),
            'emailtemplates', template_mail)
        template = open(template_file).read()
        message = template % replacements

        fromaddress = 'Rosetta SWAT Team <rosetta@ubuntu.com>'
        toaddress = helpers.contactEmailAddresses(self.rawimporter)

        simple_sendmail(fromaddress, toaddress, subject, message)

        # The import has been done, we mark it that way.
        self.rawimportstatus = RosettaImportStatus.IMPORTED

        # Now we update the statistics after this new import
        self.updateStatistics()

        # List of fields that would be updated.
        fields = ['header', 'topcomment', 'fuzzyheader', 'pluralforms',
                  'rawimportstatus', 'currentcount', 'updatescount',
                  'rosettacount']

        # And finally, emit the modified event.
        notify(SQLObjectModifiedEvent(self, object_before_modification, fields))

    def validExportCache(self):
        """See IPOFile."""
        if self.exportfile is None:
            return False

        if self.latestsubmission is None:
            return True

        change_time = self.latestsubmission.datecreated
        return change_time < self.exporttime

    def updateExportCache(self, contents):
        """See IPOFile."""
        alias_set = getUtility(ILibraryFileAliasSet)

        if self.variant:
            filename = '%s@%s.po' % (
                self.language.code, self.variant.encode('UTF-8'))
        else:
            filename = '%s.po' % (self.language.code)

        size = len(contents)
        file = StringIO.StringIO(contents)

        # Note that UTC_NOW is resolved to the time at the beginning of the
        # transaction. This is significant because translations could be added
        # to the database while the export transaction is in progress, and the
        # export would not include those translations. However, we want to be
        # able to compare the export time to other datetime object within the
        # same transaction -- e.g. in a call to validExportCache(). This is
        # why we call .sync() -- it turns the UTC_NOW reference into an
        # equivalent datetime object.

        self.exportfile = alias_set.create(
            filename, size, file, 'appliction/x-po')
        self.exporttime = UTC_NOW
        self.sync()

    def fetchExportCache(self):
        """Return the cached export file, if it exists, or None otherwise."""

        if self.exportfile is None:
            return None
        else:
            alias_set = getUtility(ILibraryFileAliasSet)
            return alias_set[self.exportfile].read()

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

    def invalidateCache(self):
        """See IPOFile."""
        self.exportfile = None


class DummyPOFile(RosettaStats):
    """Represents a POFile where we do not yet actually HAVE a POFile for
    that language for this template.
    """
    implements(IPOFile)
    def __init__(self, potemplate, language, owner=None, header=''):
        self.potemplate = potemplate
        self.language = language
        self.owner = owner
        self.header = header
        self.latestsubmission = None
        self.messageCount = len(potemplate)
        self.pluralforms = language.pluralforms
        self.translationpermission = self.potemplate.translationpermission
        self.lasttranslator = None
        self.contributors = []

    @property
    def title(self):
        """See IPOFile."""
        title = '%s translation of %s' % (
            self.language.displayname, self.potemplate.displayname)
        return title

    @property
    def translators(self):
        tgroups = self.potemplate.translationgroups
        ret = []
        for group in tgroups:
            translator = group.query_translator(self.language)
            if translator is not None:
                ret.append(translator)
        return ret

    def canEditTranslations(self, person):
        tperm = self.potemplate.translationpermission
        if tperm == TranslationPermission.OPEN:
            # if the translation policy is "open", then yes
            return True
        elif tperm == TranslationPermission.CLOSED:
            if person is not None:
                # if the translation policy is "closed", then check if the
                # person is in the set of translators XXX sabdfl 25/05/05 this
                # code could be improved when we have implemented CrowdControl
                translators = [t.translator for t in self.translators]
                for translator in translators:
                    if person.inTeam(translator):
                        return True
        else:
            raise NotImplementedError('Unknown permission %s' % tperm.name)

        # At this point you either got an OPEN (true) or you are not in the
        # designated translation group, so you can't edit them
        return False

    def currentCount(self):
        return 0

    def rosettaCount(self):
        return 0

    def updatesCount(self):
        return 0

    def nonUpdatesCount(self):
        return 0

    def translatedCount(self):
        return 0

    def untranslatedCount(self):
        return self.messageCount

    def currentPercentage(self):
        return 0.0

    def rosettaPercentage(self):
        return 0.0

    def updatesPercentage(self):
        return 0.0

    def nonUpdatesPercentage(self):
        return 0.0

    def translatedPercentage(self):
        return 0.0

    def untranslatedPercentage(self):
        return 100.0


class POFileSet:
    implements(IPOFileSet)

    def getPOFilesPendingImport(self):
        """See IPOFileSet."""
        results = POFile.selectBy(
            rawimportstatus=RosettaImportStatus.PENDING,
            orderBy='-daterawimport')

        for pofile in results:
            yield pofile

    def getDummy(self, potemplate, language):
        return DummyPOFile(potemplate, language)

