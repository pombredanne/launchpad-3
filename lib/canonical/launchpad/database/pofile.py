import StringIO, base64

# Zope interfaces
from zope.interface import implements
from zope.component import getUtility

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote

from datetime import datetime
from sets import Set

# canonical imports
from canonical.launchpad.interfaces import IPOTemplate, IPOTMsgSet, \
    IEditPOTemplate, IEditPOTMsgSet, IPOMsgID, IPOMsgIDSighting, IPOFile, \
    IEditPOFile, IPOMsgSet, IEditPOMsgSet, IPOTranslation, \
    IPOTranslationSighting, IPersonSet, IRosettaStats
from canonical.launchpad.interfaces import ILanguageSet
from canonical.launchpad.database.language import Language
from canonical.lp.dbschema import RosettaTranslationOrigin
from canonical.lp.dbschema import RosettaImportStatus
from canonical.database.constants import DEFAULT, UTC_NOW

from canonical.rosetta.pofile_adapters import TemplateImporter, POFileImporter

standardPOTemplateCopyright = 'Canonical Ltd'

# XXX: in the four strings below, we should fill in owner information
standardPOTemplateTopComment = ''' PO template for %(productname)s
 Copyright (c) %(copyright)s %(year)s
 This file is distributed under the same license as the %(productname)s package.
 PROJECT MAINTAINER OR MAILING LIST <EMAIL@ADDRESS>, %(year)s.

'''

# XXX: project-id-version needs a version
standardPOTemplateHeader = (
"Project-Id-Version: %(productname)s\n"
"POT-Creation-Date: %(date)s\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE NAME <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"X-Rosetta-Version: 0.1\n"
)

standardPOFileTopComment = ''' %(languagename)s translation for %(productname)s
 Copyright (c) %(copyright)s %(year)s
 This file is distributed under the same license as the %(productname)s package.
 FIRST AUTHOR <EMAIL@ADDRESS>, %(year)s.

'''

standardPOFileHeader = (
"Project-Id-Version: %(productname)s\n"
"Report-Msgid-Bugs-To: FULL NAME <EMAIL@ADDRESS>\n"
"POT-Creation-Date: %(templatedate)s\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: %(languagename)s <%(languagecode)s@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"X-Rosetta-Version: 0.1\n"
"Plural-Forms: nplurals=%(nplurals)d; plural=%(pluralexpr)s\n"
)

class RosettaStats(object):
    implements(IRosettaStats)

    def messageCount(self):
        # This method should be overrided by the objects that inherit from
        # this object.
        return 0

    def currentCount(self, language=None):
        # This method should be overrided by the objects that inherit from
        # this object.
        return 0

    def currentPercent(self, language=None):
        try:
            percent = float(self.currentCount(language)) / self.messageCount()
            percent *= 100
        except ZeroDivisionError:
            percent = 0
        percent = round(percent, 2)
        # We use float(str()) to prevent problems with some floating point
        # representations that could give us:
        # >>> x = 3.141592
        # >>> round(x, 2)
        # 3.1400000000000001
        # >>>
        return float(str(percent))

    def updatesCount(self, language=None):
        # This method should be overrided by the objects that inherit from
        # this object.
        return 0

    def updatesPercent(self, language=None):
        try:
            percent = float(self.updatesCount(language)) / self.messageCount()
            percent *= 100
        except ZeroDivisionError:
            percent = 0
        percent = round(percent, 2)
        return float(str(percent))

    def rosettaCount(self, language=None):
        # This method should be overrided by the objects that inherit from
        # this object.
        return 0

    def rosettaPercent(self, language=None):
        try:
            percent = float(self.rosettaCount(language)) / self.messageCount()
            percent *= 100
        except ZeroDivisionError:
            percent = 0
        percent = round(percent, 2)
        return float(str(percent))

    def translatedCount(self, language=None):
        return self.currentCount(language) + self.rosettaCount(language)

    def translatedPercent(self, language=None):
        try:
            percent = float(self.translatedCount(language)) / self.messageCount()
            percent *= 100
        except ZeroDivisionError:
            percent = 0
        percent = round(percent, 2)
        return float(str(percent))

    def untranslatedCount(self, language=None):
        untranslated = self.messageCount() - self.translatedCount(language)
        # We do a small sanity check so we don't return negative numbers.
        if untranslated < 0:
            return 0
        else:
            return untranslated

    def untranslatedPercent(self, language=None):
        try:
            percent = float(self.untranslatedCount(language)) / self.messageCount()
            percent *= 100
        except ZeroDivisionError:
            percent = 100
        percent = round(percent, 2)
        return float(str(percent))


class POTemplate(SQLBase, RosettaStats):
    implements(IEditPOTemplate)

    _table = 'POTemplate'

    product = ForeignKey(foreignKey='Product', dbName='product', notNull=True)
    priority = IntCol(dbName='priority', notNull=False, default=None)
    branch = ForeignKey(foreignKey='Branch', dbName='branch', notNull=False,
        default=None)
    changeset = ForeignKey(foreignKey='Changeset', dbName='changeset',
        notNull=False, default=None)
    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=False, default=None)
    copyright = StringCol(dbName='copyright', notNull=False, default=None)
#   license = ForeignKey(foreignKey='License', dbName='license', notNull=True)
    license = IntCol(dbName='license', notNull=False, default=None)
    datecreated = DateTimeCol(dbName='datecreated', default=DEFAULT)
    path = StringCol(dbName='path', notNull=False, default=None)
    iscurrent = BoolCol(dbName='iscurrent', notNull=True)
    messagecount = IntCol(dbName='messagecount', notNull=True, default=0)
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=False,
        default=None)
    rawfile = StringCol(dbName='rawfile', notNull=False, default=None)
    rawimporter = ForeignKey(foreignKey='Person', dbName='rawimporter',
        notNull=False, default=None)
    daterawimport = DateTimeCol(dbName='daterawimport', notNull=False,
        default=None)
    rawimportstatus = IntCol(dbName='rawimportstatus', notNull=True,
        default=RosettaImportStatus.IGNORE.value)

    poFiles = MultipleJoin('POFile', joinColumn='potemplate')


    def currentMessageSets(self):
        return POTMsgSet.select(
            '''
            POTMsgSet.potemplate = %d AND
            POTMsgSet.sequence > 0
            '''
            % self.id, orderBy='sequence')

    def __len__(self):
        '''Return the number of CURRENT POTMsgSets in this POTemplate.'''
        return self.messageCount()

    def __iter__(self):
            return iter(self.currentMessageSets())

    def messageSet(self, key, onlyCurrent=False):
        query = '''potemplate = %d''' % self.id
        if onlyCurrent:
            query += ' AND sequence > 0'

        if isinstance(key, slice):
            return POTMsgSet.select(query, orderBy='sequence')[key]

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

        results = POTMsgSet.select(query +
            (' AND primemsgid = %d' % messageID.id))

        if results.count() == 0:
            raise KeyError, key
        else:
            assert results.count() == 1

            return results[0]

    def __getitem__(self, key):
        return self.messageSet(key, onlyCurrent=True)

    def filterMessageSets(self, current, translated, languages, slice = None):
        '''
        Return message sets from this PO template, filtered by various
        properties.

        current:
            Whether the message sets need be complete or not.
        translated:
            Wether the messages sets need be translated in the specified
            languages or not.
        languages:
            The languages used for testing translatedness.
        slice:
            The range of results to be selected, or None, for all results.
        '''

        if current is not None:
            if current:
                current_condition = 'POTMsgSet.sequence > 0'
            else:
                current_condition = 'POTMsgSet.sequence = 0'
        else:
            current_condition = 'TRUE'

        # Assuming that for each language being checked, each POT mesage set
        # has a corresponding PO message set for that language:
        #
        # A POT set is translated if all its PO message sets have iscomplete =
        # TRUE. In other words, none of its PO message sets have iscomplete =
        # FALSE.
        #
        # A POT set is untranslated if any of its PO message set has
        # iscomplete = FALSE. In other words, not all of its PO message sets
        # have iscomplete = TRUE.
        #
        # The possible non-existance of corresponding PO message sets
        # complicates matters a bit:
        #
        # - For translated == True, missing PO message sets must make the
        #   condition evaluate to FALSE.
        #
        # - For translated == False, missing PO message sets must make the
        #   condition evaluate to TRUE.
        #
        # So, we get around this problem by checking the number of PO message
        # sets against the number of languages.

        language_codes = ', '.join([ "'%s'" % str(l.code) for l in languages ])

        if translated is not None:
            # Search for PO message sets which aren't complete for this POT
            # set.
            subquery1 = '''
                SELECT poset.id FROM POMsgSet poset, POFile pofile,
                        Language language WHERE
                    poset.potmsgset = POTMsgSet.id AND
                    poset.pofile = pofile.id AND
                    pofile.language = language.id AND
                    language.code IN (%s) AND
                    iscomplete = FALSE
                ''' % language_codes

            # Count PO message sets for this POT set.
            subquery2 = '''
                SELECT COUNT(poset.id) FROM POMsgSet poset, POFile pofile,
                        Language language WHERE
                    poset.potmsgset = POTMsgSet.id AND
                    poset.pofile = pofile.id AND
                    pofile.language = language.id AND
                    language.code IN (%s)
                ''' % language_codes

            if translated:
                translated_condition = ('NOT EXISTS (%s) AND (%s) = %d' %
                    (subquery1, subquery2, len(languages)))
            else:
                translated_condition = ('EXISTS (%s) OR (%s) < %d' %
                    (subquery1, subquery2, len(languages)))
        else:
            translated_condition = 'TRUE'

        results = POTMsgSet.select(
            'POTMsgSet.potemplate = %d AND (%s) AND (%s) '
                % (self.id, translated_condition, current_condition),
                orderBy = 'POTMsgSet.sequence')

        if slice is not None:
            return results[slice]
        else:
            return results

    def languages(self):
        '''This returns the set of languages for which we have
        POFiles for this POTemplate. NOTE that variants are simply
        ignored, if we have three variants for en_GB we will simply
        return a single record for en_GB.'''

        # XXX: Carlos Perello Marin 15/10/04: As SQLObject does not have
        # SELECT DISTINCT we use Sets, as soon as it's fixed we should change
        # this.
        return Set(Language.select('''
            POFile.language = Language.id AND
            POFile.potemplate = %d
            ''' % self.id, clauseTables=('POFile', 'Language')))

    def poFilesToImport(self):
        for pofile in iter(self.poFiles):
            if pofile.rawimportstatus == RosettaImportStatus.PENDING:
                yield pofile

    def getPOFileByLang(self, language_code, variant=None):
        if variant is None:
            variantspec = 'IS NULL'
        elif isinstance(variant, unicode):
            variantspec = (u'= "%s"' % quote(variant))
        else:
            raise TypeError('Variant must be None or unicode.')

        ret = POFile.select("""
            POFile.potemplate = %d AND
            POFile.language = Language.id AND
            POFile.variant %s AND
            Language.code = %s
            """ % (self.id,
                   variantspec,
                   quote(language_code)),
            clauseTables=('Language',))

        if ret.count() == 0:
            raise KeyError, 'PO File for %s does not exist' % language_code
        else:
            return ret[0]

    def queryPOFileByLang(self, language_code, variant=None):
        try:
            pofile = self.getPOFileByLang(language_code, variant)
            return pofile
        except KeyError:
            return None

    def messageCount(self):
        return self.messagecount

    def currentCount(self, language):
        try:
            return self.getPOFileByLang(language).currentCount()
        except KeyError:
            return 0

    def updatesCount(self, language):
        try:
            return self.getPOFileByLang(language).updatesCount()
        except KeyError:
            return 0

    def rosettaCount(self, language):
        try:
            return self.getPOFileByLang(language).rosettaCount()
        except KeyError:
            return 0

    def hasMessageID(self, messageID):
        results = POTMsgSet.select('''
            POTMsgSet.potemplate = %d AND
            POTMsgSet.primemsgid = %d''' % (self.id, messageID.id))

        return results.count() > 0

    def hasPluralMessage(self):
        results = POMsgIDSighting.select('''
            pluralform = 1 AND
            potmsgset IN (SELECT id FROM POTMsgSet WHERE potemplate = %d)
            ''' % self.id)

        return results.count() > 0

    # Methods defined in IEditPOTemplate

    def expireAllMessages(self):
        self._connection.query('UPDATE POTMsgSet SET sequence = 0'
                               ' WHERE potemplate = %d'
                               % self.id)

    def getOrCreatePOFile(self, language_code, variant=None, owner=None):
        # see if one exists already
        existingpo = self.queryPOFileByLang(language_code, variant)
        if existingpo is not None:
            return existingpo

        # since we don't have one, create one
        try:
            language = Language.byCode(language_code)
        except SQLObjectNotFound:
            raise ValueError, "Unknown language code '%s'" % language_code

        now = datetime.now()
        data = {
            'year': now.year,
            'languagename': language.englishname,
            'languagecode': language_code,
            'productname': self.product.title,
            'date': now.isoformat(' '),
            # XXX: This is not working and I'm not able to fix it easily
            #'templatedate': self.datecreated.gmtime().Format('%Y-%m-%d %H:%M+000'),
            'templatedate': self.datecreated,
            'copyright': '(c) %d Canonical Ltd, and Rosetta Contributors' % now.year,
            'nplurals': language.pluralforms or 1,
            'pluralexpr': language.pluralexpression or '0',
            }

        return POFile(potemplate=self,
                      language=language,
                      title='Rosetta %(languagename)s translation of %(productname)s' % data,
                      topcomment=standardPOFileTopComment % data,
                      header=standardPOFileHeader % data,
                      fuzzyheader=True,
                      owner=owner,
                      pluralforms=data['nplurals'],
                      variant=variant)

    def createMessageIDSighting(self, potmsgset, messageID):
        """Creates in the database a new message ID sighting.

        Returns None.
        """

        POMsgIDSighting(
            potmsgsetID=potmsgset.id,
            pomsgid_ID=messageID.id,
            datefirstseen=UTC_NOW,
            datelastseen=UTC_NOW,
            inlastrevision=True,
            pluralform=0)

    def createMessageSetFromMessageID(self, messageID):
        """Creates in the database a new message set.

        As a side-effect, creates a message ID sighting in the database for the
        new set's prime message ID.

        Returns that message set.
        """
        messageSet = POTMsgSet(
            primemsgid_=messageID,
            sequence=0,
            potemplate=self,
            commenttext=None,
            filereferences=None,
            sourcecomment=None,
            flagscomment=None)

        self.createMessageIDSighting(messageSet, messageID)

        return messageSet

    def createMessageSetFromText(self, text):
        # This method used to accept 'text' parameters being string objects,
        # but this is depracated.
        if not isinstance(text, unicode):
            raise TypeError("Message ID text must be unicode.")

        try:
            messageID = POMsgID.byMsgid(text)
            if self.hasMessageID(messageID):
                raise KeyError(
                    "There is already a message set for this template, file "
                    "and primary msgid")
        except SQLObjectNotFound:
            # If there are no existing message ids, create a new one.
            # We do not need to check whether there is already a message set
            # with the given text in this template.
            messageID = POMsgID(msgid=text)

        return self.createMessageSetFromMessageID(messageID)

    def doRawImport(self):
        importer = TemplateImporter(self, self.rawimporter)
    
        file = StringIO.StringIO(base64.decodestring(self.rawfile))
    
        try:
            importer.doImport(file)
        except:
            # The import failed, we mark it as failed so we could review it
            # later in case it's a bug in our code.
            self.rawimportstatus = RosettaImportStatus.FAILED.value
        else:
            # The import has been done, we mark it that way.
            self.rawimportstatus = RosettaImportStatus.IMPORTED.value

        # We update the cached value that tells us the number of msgsets this
        # .pot file has
        self.messagecount = self.currentMessageSets().count()

        # And now, we should update the statistics for all po files this .pot
        # file has because a number of msgsets could have change.
        # XXX: Carlos Perello Marin 09/12/2004 We should handle this case
        # better. The pofile don't get updated the currentcount updated...
        for pofile in self.poFiles:
            pofile.updateStatistics()


class POTMsgSet(SQLBase):
    implements(IPOTMsgSet)

    _table = 'POTMsgSet'

    primemsgid_ = ForeignKey(foreignKey='POMsgID', dbName='primemsgid',
        notNull=True)
    sequence = IntCol(dbName='sequence', notNull=True)
    potemplate = ForeignKey(foreignKey='POTemplate', dbName='potemplate',
        notNull=True)
    commenttext = StringCol(dbName='commenttext', notNull=False)
    filereferences = StringCol(dbName='filereferences', notNull=False)
    sourcecomment = StringCol(dbName='sourcecomment', notNull=False)
    flagscomment = StringCol(dbName='flagscomment', notNull=False)

    def flags(self):
        if self.flagscomment is None:
            return ()
        else:
            return [ flag for flag in
                self.flagscomment.replace(' ', '').split(',') if flag != '' ]

    # XXX: Carlos Perello Marin 15/10/04: Review, not sure it's correct...
    # XXX: Carlos Perello Marin 18/10/04: We should not return SQLRecordSets
    # in our interface, we should fix it after the split.
    def messageIDs(self):
        return POMsgID.select('''
            POMsgIDSighting.potmsgset = %d AND
            POMsgIDSighting.pomsgid = POMsgID.id AND
            POMsgIDSighting.inlastrevision = TRUE
            ''' % self.id, clauseTables=('POMsgIDSighting',),
            orderBy='POMsgIDSighting.pluralform')

    # XXX: Carlos Perello Marin 15/10/04: Review, not sure it's correct...
    def getMessageIDSighting(self, pluralForm, allowOld=False):
        """Return the message ID sighting that is current and has the
        plural form provided."""
        if allowOld:
            results = POMsgIDSighting.selectBy(
                potmsgsetID=self.id,
                pluralform=pluralForm)
        else:
            results = POMsgIDSighting.selectBy(
                potmsgsetID=self.id,
                pluralform=pluralForm,
                inlastrevision=True)

        if results.count() == 0:
            raise KeyError, pluralForm
        else:
            assert results.count() == 1

            return results[0]

    def poMsgSet(self, language_code, variant=None):
        if variant is None:
            variantspec = 'IS NULL'
        elif isinstance(variant, unicode):
            variantspec = (u'= "%s"' % quote(variant))
        else:
            raise TypeError('Variant must be None or unicode.')

        sets = POMsgSet.select('''
            POMsgSet.potmsgset = %d AND
            POMsgSet.pofile = POFile.id AND
            POFile.language = Language.id AND
            POFile.variant %s AND
            Language.code = %s
            ''' % (self.id,
                   variantspec,
                   quote(language_code)),
            clauseTables=('POFile', 'Language'))

        if sets.count() == 0:
            raise KeyError, (language_code, variant)
        else:
            return sets[0]

    def translationsForLanguage(self, language):
        # Find the number of plural forms.

        # XXX: Not sure if falling back to the languages table is the right
        # thing to do.
        languages = getUtility(ILanguageSet)

        try:
            pofile = self.potemplate.getPOFileByLang(language)
            pluralforms = pofile.pluralforms
        except KeyError:
            pofile = None
            pluralforms = languages[language].pluralforms

        # If we only have a msgid, we change pluralforms to 1, if it's a
        # plural form, it will be the number defined in the pofile header.
        if self.messageIDs().count() == 1:
            pluralforms = 1

        if pluralforms == None:
            raise RuntimeError(
                "Don't know the number of plural forms for this PO file!")

        if pofile is None:
            return [None] * pluralforms

        # Find the sibling message set.

        results = POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.primemsgid = %d'''
           % (pofile.id, self.primemsgid_.id),
           clauseTables = ['POTMsgSet', ])

        if not (0 <= results.count() <= 1):
            raise AssertionError("Duplicate message ID in PO file.")

        if results.count() == 0:
            return [None] * pluralforms

        translation_set = results[0]

        results = list(POTranslationSighting.select(
            'pomsgset = %d AND active = TRUE' % translation_set.id,
            orderBy='pluralForm'))

        translations = []

        for form in range(pluralforms):
            if results and results[0].pluralform == form:
                translations.append(results.pop(0).potranslation.translation)
            else:
                translations.append(None)

        return translations

    # Methods defined in IEditPOTMsgSet

    def makeMessageIDSighting(self, text, pluralForm, update=False):
        """Create a new message ID sighting for this message set."""

        # This method used to accept 'text' parameters being string objects,
        # but this is depracated.
        if not isinstance(text, unicode):
            raise TypeError("Message ID text must be unicode.")

        try:
            messageID = POMsgID.byMsgid(text)
        except SQLObjectNotFound:
            messageID = POMsgID(msgid=text)

        existing = POMsgIDSighting.selectBy(
            potmsgsetID=self.id,
            pomsgid_ID=messageID.id,
            pluralform=pluralForm)

        if existing.count():
            assert existing.count() == 1

            if not update:
                raise KeyError(
                    "There is already a message ID sighting for this "
                    "message set, text, and plural form")

            existing = existing[0]
            existing.set(datelastseen = UTC_NOW, inlastrevision = True)

            return existing

        return POMsgIDSighting(
            potmsgsetID=self.id,
            pomsgid_ID=messageID.id,
            datefirstseen=UTC_NOW,
            datelastseen=UTC_NOW,
            inlastrevision=True,
            pluralform=pluralForm)


class POMsgIDSighting(SQLBase):
    implements(IPOMsgIDSighting)

    _table = 'POMsgIDSighting'

    potmsgset = ForeignKey(foreignKey='POTMsgSet', dbName='potmsgset',
        notNull=True)
    pomsgid_ = ForeignKey(foreignKey='POMsgID', dbName='pomsgid',
        notNull=True)
    datefirstseen = DateTimeCol(dbName='datefirstseen', notNull=True)
    datelastseen = DateTimeCol(dbName='datelastseen', notNull=True)
    inlastrevision = BoolCol(dbName='inlastrevision', notNull=True)
    pluralform = IntCol(dbName='pluralform', notNull=True)


class POMsgID(SQLBase):
    implements(IPOMsgID)

    _table = 'POMsgID'

    msgid = StringCol(dbName='msgid', notNull=True, unique=True,
        alternateID=True)


class POFile(SQLBase, RosettaStats):
    implements(IEditPOFile)

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
                       notNull=False,
                       default=None)
    pluralforms = IntCol(dbName='pluralforms',
                         notNull=True)
    variant = StringCol(dbName='variant',
                        notNull=False,
                        default=None)
    filename = StringCol(dbName='filename',
                         notNull=False,
                         default=None)
    rawfile = StringCol(dbName='rawfile',
                        notNull=False,
                        default=None)
    rawimporter = ForeignKey(foreignKey='Person',
                             dbName='rawimporter',
                             notNull=False,
                             default=None)
    daterawimport = DateTimeCol(dbName='daterawimport',
                                notNull=False,
                                default=None)
    rawimportstatus = IntCol(dbName='rawimportstatus',
                             notNull=False,
                             default=RosettaImportStatus.IGNORE.value)


    def currentMessageSets(self):
        return POMsgSet.select(
            '''
            POMsgSet.pofile = %d AND
            POMsgSet.sequence > 0
            '''
            % self.id, orderBy='sequence')

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
            clauseTables = [
                'POMsgSet',
                ]))

    def untranslated(self):
        '''XXX'''
        raise NotImplementedError

    def __iter__(self):
        return iter(self.currentMessageSets())

    def messageSet(self, key, onlyCurrent=False):
        query = '''potemplate = %d''' % self.potemplate.id
        if onlyCurrent:
            query += ' AND sequence > 0'

        if isinstance(key, slice):
            # XXX: Carlos Perello Marin 19/10/04: Not sure how to handle this.
            raise NotImplementedError
#           return POTMsgSet.select(query, orderBy='sequence')[key]

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

        results = POTMsgSet.select(query +
            (' AND primemsgid = %d' % messageID.id))

        if results.count() == 0:
            raise KeyError, key
        else:
            assert results.count() == 1

            poresults = POMsgSet.selectBy(
                potmsgsetID=results[0].id,
                pofileID=self.id)

            if poresults.count() == 0:
                raise KeyError, key
            else:
                assert poresults.count() == 1

                return poresults[0]

    def __getitem__(self, msgid_text):
        return self.messageSet(msgid_text)

    def messageSetsNotInTemplate(self):
        return iter(POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POMsgSet.sequence <> 0 AND
            POTMsgSet.sequence = 0''' % self.id,
            clauseTables = [
                'POTMsgSet',
                ]))

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
        self._connection.query(
            '''UPDATE POMsgSet SET sequence = 0 WHERE pofile = %d'''
            % self.id)

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
            ''' % self.id, clauseTables=('POTMsgSet',)).count()
        else:
            current = self.currentcount

        # XXX: Carlos Perello Marin 27/10/04: We should fix the schema if we
        # want that updates/rosetta is correctly calculated, if we have fuzzy msgset
        # and then we fix it from Rosetta it will be counted as an update when
        # it's not.
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
            ''' % self.id, clauseTables=('POTMsgSet', )).count()

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
            ''' % self.id, clauseTables=('POTMsgSet',)).count()
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

    def lastChangedSighting(self):
        '''
        SELECT * FROM POTranslationSighting WHERE POTranslationSighting.id =
        POMsgSet.id AND POMsgSet.pofile = 2 ORDER BY datelastactive;
        '''
        sightings = POTranslationSighting.select('''
            POTranslationSighting.pomsgset = POMsgSet.id AND
            POMsgSet.pofile = %d''' % self.id, orderBy='-datelastactive',
            clauseTables=('POMsgSet',))

        try:
            return sightings[0]
        except IndexError:
            return None

    def doRawImport(self):
        importer = POFileImporter(self, self.rawimporter)

        import pdb
        pdb.set_trace()
    
        file = StringIO.StringIO(base64.decodestring(self.rawfile))
    
        try:
            importer.doImport(file)
        except:
            self.rawimportstatus = RosettaImportStatus.FAILED.value
        else:
            self.rawimportstatus = RosettaImportStatus.IMPORTED.value

        # Now we update the statistics after this new import
        self.updateStatistics(newImport=True)


class POMsgSet(SQLBase):
    implements(IEditPOMsgSet)

    _table = 'POMsgSet'

    sequence = IntCol(dbName='sequence', notNull=True)
    pofile = ForeignKey(foreignKey='POFile', dbName='pofile', notNull=True)
    iscomplete = BoolCol(dbName='iscomplete', notNull=True)
    obsolete = BoolCol(dbName='obsolete', notNull=True)
    fuzzy = BoolCol(dbName='fuzzy', notNull=True)
    commenttext = StringCol(dbName='commenttext', notNull=False, default=None)
    potmsgset = ForeignKey(foreignKey='POTMsgSet', dbName='potmsgset',
        notNull=True)

    def pluralforms(self):
        if self.potmsgset.messageIDs().count() > 1:
            # has plurals
            return self.pofile.pluralforms
        else:
            # message set is singular
            return 1

    def translations(self):
        pluralforms = self.pluralforms()
        if pluralforms is None:
            raise RuntimeError(
                "Don't know the number of plural forms for this PO file!")

        results = list(POTranslationSighting.select(
            'pomsgset = %d AND active = TRUE' % self.id,
            orderBy='pluralForm'))

        translations = []

        for form in range(pluralforms):
            if results and results[0].pluralform == form:
                translations.append(results.pop(0).potranslation.translation)
            else:
                translations.append(None)

        return translations

    # XXX: Carlos Perello Marin 15/10/04: Review this method, translations
    # could have more than one row and we always return only the firts one!
    def getTranslationSighting(self, pluralForm, allowOld=False):
        """Return the translation sighting that is committed and has the
        plural form specified."""
        if allowOld:
            translations = POTranslationSighting.selectBy(
                pomsgsetID=self.id,
                pluralform=pluralForm)
        else:
            translations = POTranslationSighting.selectBy(
                pomsgsetID=self.id,
                inlastrevision=True,
                pluralform=pluralForm)
        if translations.count() == 0:
            raise IndexError, pluralForm
        else:
            return translations[0]

    def translationSightings(self):
        return POTranslationSighting.selectBy(
            pomsgsetID=self.id)

    # IEditPOMsgSet

    def updateTranslation(self, person, new_translations, fuzzy, fromPOFile):
        was_complete = self.iscomplete
        was_fuzzy = self.fuzzy
        has_changes = False
        # By default we will think that all translations for this pomsgset
        # where available in last import
        all_in_last_revision = True

        # Get a hold of a list of existing translations for the message set.
        old_translations = self.translations()

        for index in new_translations.keys():
            # For each translation, add it to the database if it is
            # non-null and different to the old one.
            if new_translations[index] != old_translations[index]:
                has_changes = True
                if (new_translations[index] == '' or
                    new_translations[index] is None):
                    # Make all sightings inactive.

                    self._connection.query(
                        '''
                            UPDATE POTranslationSighting SET active = FALSE
                            WHERE
                                pomsgset = %d AND
                                pluralform = %d
                        ''' % (self.id, index))
                    new_translations[index] = None
                    self.iscomplete = False

                else:
                    try:
                        old_sight = self.getTranslationSighting(index)
                    except IndexError:
                        # We don't have a sighting for this string, that means
                        # that either the translation is new or that the old
                        # translation does not comes from the pofile.
                        all_in_last_revision = False
                    else:
                        if not old_sight.active:
                            all_in_last_revision = False
                    self.makeTranslationSighting(
                        person = person,
                        text = new_translations[index],
                        pluralForm = index,
                        fromPOFile = fromPOFile)

        # We set the fuzzy flag as needed:
        if fuzzy and self.fuzzy == False:
            self.fuzzy = True
            has_changes = True
        elif not fuzzy and self.fuzzy == True:
            self.fuzzy = False
            has_changes = True
        
        if not has_changes:
            # We don't change the statistics if we didn't had any change.
            return
            
        # We do now a live update of the statistics.
        if self.iscomplete and not self.fuzzy:
            # New msgset translation is ready to be used.
            if not was_complete or was_fuzzy:
                # It was not ready before this change.
                if fromPOFile:
                    # The change was done outside Rosetta.
                    self.pofile.currentcount += 1
                else:
                    # The change was done with Rosetta.
                    self.pofile.rosettacount += 1
            elif not fromPOFile and all_in_last_revision:
                # We have updated a translation from Rosetta that was
                # already translated.
                self.pofile.updatescount += 1
        else:
            # This new msgset translation is not yet finished.
            if was_complete and not was_fuzzy:
                # But previously it was finished, so we lost its translation.
                if fromPOFile:
                    # It was lost outside Rosetta
                    self.pofile.currentcount -= 1
                else:
                    # It was lost inside Rosetta
                    self.pofile.rosettacount -= 1

        # XXX: Carlos Perello Marin 10/12/2004 Sanity test, the statistics
        # code is not as good as it should, we can get negative numbers, in
        # case we reach that status, we just change that field to 0.
        if self.pofile.currentcount < 0:
            self.pofile.currentcount = 0
        if self.pofile.rosettacount < 0:
            self.pofile.rosettacount = 0
                
                
    def makeTranslationSighting(self, person, text, pluralForm,
        fromPOFile=False):
        """Create a new translation sighting for this message set."""

        # First get hold of a POTranslation for the specified text.
        try:
            translation = POTranslation.byTranslation(text)
        except SQLObjectNotFound:
            translation = POTranslation(translation=text)

        # Now get hold of any existing translation sightings.

        results = POTranslationSighting.selectBy(
            pomsgsetID=self.id,
            potranslationID=translation.id,
            pluralform=pluralForm,
            personID=person.id)

        if results.count():
            # A sighting already exists.

            assert results.count() == 1

            sighting = results[0]
            sighting.set(
                datelastactive = UTC_NOW,
                active = True,
                # XXX: Ugly!
                # XXX: Carlos Perello Marin 05/10/04 Why is ugly?
                inlastrevision = sighting.inlastrevision or fromPOFile)
        else:
            # No sighting exists yet.

            if fromPOFile:
                origin = int(RosettaTranslationOrigin.SCM)
            else:
                origin = int(RosettaTranslationOrigin.ROSETTAWEB)

            sighting = POTranslationSighting(
                pomsgsetID=self.id,
                potranslationID=translation.id,
                datefirstseen= UTC_NOW,
                datelastactive= UTC_NOW,
                inlastrevision=fromPOFile,
                pluralform=pluralForm,
                active=True,
                personID=person.id,
                origin=origin)

        # Make all other sightings inactive.

        self._connection.query(
            '''
            UPDATE POTranslationSighting SET active = FALSE
            WHERE
                pomsgset = %d AND
                pluralform = %d AND
                id <> %d
            ''' % (self.id, pluralForm, sighting.id))

        # Implicit set of iscomplete. If we have all translations, it's 
        # complete, if we lack a translation, it's not complete.
        if None in self.translations():
            self.iscomplete = False
        else:
            self.iscomplete = True

        return sighting


class POTranslationSighting(SQLBase):
    implements(IPOTranslationSighting)

    _table = 'POTranslationSighting'

    pomsgset = ForeignKey(foreignKey='POMsgSet', dbName='pomsgset',
        notNull=True)
    potranslation = ForeignKey(foreignKey='POTranslation',
        dbName='potranslation', notNull=True)
#   license = ForeignKey(foreignKey='License', dbName='license', notNull=True)
    license = IntCol(dbName='license', notNull=True)
    datefirstseen = DateTimeCol(dbName='datefirstseen', notNull=True)
    datelastactive = DateTimeCol(dbName='datelastactive', notNull=True)
    inlastrevision = BoolCol(dbName='inlastrevision', notNull=True)
    pluralform = IntCol(dbName='pluralform', notNull=True)
    active = BoolCol(dbName='active', notNull=True, default=DEFAULT)
    # See canonical.lp.dbschema.RosettaTranslationOrigin.
    origin = IntCol(dbName='origin', notNull=True)
    person = ForeignKey(foreignKey='Person', dbName='person', notNull=True)


class POTranslation(SQLBase):
    implements(IPOTranslation)

    _table = 'POTranslation'

    translation = StringCol(dbName='translation', notNull=True, unique=True,
        alternateID=True)

