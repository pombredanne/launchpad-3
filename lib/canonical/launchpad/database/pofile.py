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
from canonical.launchpad.interfaces.pofile import IPOTemplate, IPOTMsgSet, \
    IEditPOTemplate, IEditPOTMsgSet, IPOMsgID, IPOMsgIDSighting, IPOFile, \
    IEditPOFile, IPOMsgSet, IEditPOMsgSet, IPOTranslation, \
    IPOTranslationSighting
from canonical.launchpad.interfaces.language import ILanguageSet
from canonical.launchpad.database.language import Language
from canonical.lp.dbschema import RosettaTranslationOrigin
from canonical.database.constants import DEFAULT, UTC_NOW

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


class POTemplate(SQLBase):
    implements(IEditPOTemplate)

    _table = 'POTemplate'

    _columns = [
        ForeignKey(name='product', foreignKey='Product', dbName='product',
            notNull=True),
        IntCol(name='priority', dbName='priority', notNull=True),
        ForeignKey(name='branch', foreignKey='Branch', dbName='branch',
            notNull=True),
        ForeignKey(name='changeset', foreignKey='Changeset',
            dbName='changeset', notNull=False, default=None),
        StringCol(name='name', dbName='name', notNull=True),
        StringCol(name='title', dbName='title', notNull=True),
        StringCol(name='description', dbName='description', notNull=True),
        StringCol(name='copyright', dbName='copyright', notNull=True),
#        ForeignKey(name='license', foreignKey='License', dbName='license',
#            notNull=True),
        IntCol(name='license', dbName='license', notNull=True),
        DateTimeCol(name='datecreated', dbName='datecreated', default=DEFAULT),
        StringCol(name='path', dbName='path', notNull=True),
        BoolCol(name='iscurrent', dbName='iscurrent', notNull=True),
        IntCol(name='messagecount', dbName='messagecount', notNull=True),
        ForeignKey(name='owner', foreignKey='Person', dbName='owner',
            notNull=False, default=None),
    ]

    
    def currentMessageSets(self):
        return POTMsgSet.select(
            '''
            POTMsgSet.potemplate = %d AND
            POTMsgSet.sequence > 0
            '''
            % self.id, orderBy='sequence')

    def __len__(self):
        '''Return the number of CURRENT POTMsgSets in this POTemplate.'''
        # XXX: Carlos Perello Marin XX/XX/04 Should we use the cached value
        # POTemplate.messageCount instead?
        return self.currentMessageSets().count()

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

    _poFilesJoin = MultipleJoin('POFile', joinColumn='potemplate')

    def poFiles(self):
        return iter(self._poFilesJoin)

    def poFile(self, language_code, variant=None):
        if variant is None:
            variantspec = 'IS NULL'
        else:
            variantspec = (u'= "%s"' % quote(variant)).encode('utf-8')

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
            raise KeyError, language_code
        else:
            return ret[0]

    # XXX: Carlos Perello Marin: currentCount, updatesCount and rosettaCount
    # should be updated with a way that let's us query the database instead
    # of use the cached value

    def currentCount(self, language):
        try:
            return self.poFile(language).currentcount
        except KeyError:
            return 0

    def updatesCount(self, language):
        try:
            return self.poFile(language).updatescount
        except KeyError:
            return 0

    def rosettaCount(self, language):
        try:
            return self.poFile(language).rosettacount
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

    def newPOFile(self, person, language_code, variant=None):
        try:
            self.poFile(language_code, variant)
        except KeyError:
            pass
        else:
            raise KeyError(
                "This template already has a POFile for %s variant %s" %
                (language.englishName, variant))

        try:
            language = Language.byCode(language_code)
        except SQLObjectNotFound:
            raise ValueError, "Unknown language code '%s'" % language_code

        now = datetime.now()
        data = {
            'year': now.year,
            'languagename': language.englishName,
            'languagecode': language_code,
            'productname': self.product.title,
            'date': now.isoformat(' '),
            # XXX: This is not working and I'm not able to fix it easily
            #'templatedate': self.datecreated.gmtime().Format('%Y-%m-%d %H:%M+000'),
            'templatedate': self.datecreated,
            'copyright': self.copyright,
            'nplurals': language.pluralForms or 1,
            'pluralexpr': language.pluralExpression or '0',
            }

        return POFile(potemplate=self,
                      language=language,
                      title='%(languagename)s translation for %(productname)s' % data,
                      topcomment=standardPOFileTopComment % data,
                      header=standardPOFileHeader % data,
                      fuzzyheader=True,
                      lasttranslator=person,
                      currentcount=0,
                      updatescount=0,
                      rosettacount=0,
                      lastparsed=UTC_NOW,
                      owner=person,
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
        if isinstance(text, unicode):
            text = text.encode('utf-8')

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


class POTMsgSet(SQLBase):
    implements(IPOTMsgSet)

    _table = 'POTMsgSet'

    _columns = [
        ForeignKey(name='primemsgid_', foreignKey='POMsgID',
            dbName='primemsgid', notNull=True),
        IntCol(name='sequence', dbName='sequence', notNull=True),
        ForeignKey(name='potemplate', foreignKey='POTemplate',
            dbName='potemplate', notNull=True),
        StringCol(name='commenttext', dbName='commenttext', notNull=False),
        StringCol(name='filereferences', dbName='filereferences', notNull=False),
        StringCol(name='sourcecomment', dbName='sourcecomment', notNull=False),
        StringCol(name='flagscomment', dbName='flagscomment', notNull=False),
    ]

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

    def translationsForLanguage(self, language):
        # Find the number of plural forms.

        # XXX: Not sure if falling back to the languages table is the right
        # thing to do.
        languages = getUtility(ILanguageSet)

        try:
            pofile = self.potemplate.poFile(language)
            pluralforms = pofile.pluralforms
        except KeyError:
            pofile = None
            pluralforms = languages[language].pluralForms

        # XXX: Carlos Perello Marin 15/10/04 WHY??
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
           % (pofile.id, self.primemsgid_.id))

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

        if type(text) is unicode:
            text = text.encode('utf-8')

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

    _columns = [
        ForeignKey(name='potmsgset', foreignKey='POTMsgSet',
            dbName='potmsgset', notNull=True),
        ForeignKey(name='pomsgid_', foreignKey='POMsgID', dbName='pomsgid',
            notNull=True),
        DateTimeCol(name='datefirstseen', dbName='datefirstseen',
            notNull=True),
        DateTimeCol(name='datelastseen', dbName='datelastseen', notNull=True),
        BoolCol(name='inlastrevision', dbName='inlastrevision', notNull=True),
        IntCol(name='pluralform', dbName='pluralform', notNull=True),
    ]


class POMsgID(SQLBase):
    implements(IPOMsgID)

    _table = 'POMsgID'

    _columns = [
        StringCol(name='msgid', dbName='msgid', notNull=True, unique=True,
            alternateID=True)
    ]


class POFile(SQLBase):
    implements(IEditPOFile)

    _table = 'POFile'

    _columns = [
        ForeignKey(name='potemplate', foreignKey='POTemplate',
            dbName='potemplate', notNull=True),
        ForeignKey(name='language', foreignKey='Language', dbName='language',
            notNull=True),
        StringCol(name='title', dbName='title', notNull=False, default=None),
        StringCol(name='description', dbName='description', notNull=False,
            default=None),
        StringCol(name='topcomment', dbName='topcomment', notNull=False,
            default=None),
        StringCol(name='header', dbName='header', notNull=False, default=None),
        BoolCol(name='fuzzyheader', dbName='fuzzyheader', notNull=True),
        ForeignKey(name='lasttranslator', foreignKey='Person',
            dbName='lasttranslator', notNull=False, default=None),
#        ForeignKey(name='license', foreignKey='License', dbName='license',
#            notNull=False, default=None),
        IntCol(name='license', dbName='license', notNull=False, default=None),
        IntCol(name='currentcount', dbName='currentcount', notNull=True),
        IntCol(name='updatescount', dbName='updatescount', notNull=True),
        IntCol(name='rosettacount', dbName='rosettacount', notNull=True),
        DateTimeCol(name='lastparsed', dbName='lastparsed', notNull=False,
            default=None),
        ForeignKey(name='owner', foreignKey='Person', dbName='owner',
            notNull=False, default=None),
        IntCol(name='pluralforms', dbName='pluralforms', notNull=True),
        StringCol(name='variant', dbName='variant', notNull=False,
            default=None),
        StringCol(name='filename', dbName='filename', notNull=False,
            default=None),
    ]

    
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
        '''Count of __iter__.'''
        return self.currentMessageSets().count()

    # XXX: Carlos Perello Marin XX/XX/04: This is implemented using the cache,
    # we should add an option to get the real count.
    # The number of translated are the ones from the .po file + the ones that
    # are only translated in Rosetta.
    def translatedCount(self):
        '''Returns the cached count of translated strings where translations
        exist in the files or in the database.'''
        return self.currentcount + self.rosettacount

    def translated(self):
        return iter(POMsgSet.select('''
            POMsgSet.pofile = %d AND
            POMsgSet.iscomplete=TRUE AND
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.sequence > 0''' % self.id,
            clauseTables = [
                'POMsgSet',
                ]))

    # XXX: Carlos Perello Marin XX/XX/04: This is implemented using the cache,
    # we should add an option to get the real count.
    # The number of untranslated are the ones from the .pot file - the ones
    # that we have already translated.
    def untranslatedCount(self):
        '''Same as untranslated(), but with COUNT.'''
        return len(self.potemplate) - self.translatedCount()

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
            RunTimeError('Implement me!!')
#            return POTMsgSet.select(query, orderBy='sequence')[key]

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

            poresults = POMsgSet.selectBy(potmsgsetID=results[0].id)

            if poresults.count() == 0:
                raise KeyError, key
            else:
                assert poresults.count() == 1

                return poresults[0]

    
    def __getitem__(self, msgid_text):
        return self.messageSet(msgid_text, onlyCurrent=True)

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

    # IEditPOFile

    def expireAllMessages(self):
        self._connection.query(
            '''UPDATE POMsgSet SET sequence = 0 WHERE pofile = %d'''
            % self.id)
    
    def updateStatistics(self):
        # XXX: Carlos Perello Marin 19/10/04 Disabled, we need to define the
        # strategy to follow about the statistics and I don't want to expend
        # too many time fixing this.
        return (0, 0, 0)
        # XXX: Carlos Perello Marin 05/10/04 This method should be reviewed
        # harder after the final decission about how should we use active and
        # inLastRevision fields.
        # I'm not doing it now because the statistics works is not completed
        # and I don't want to conflict with lalo's work.
        # XXX: Carlos Perello Marin 15/10/04: After the potmsgset and pomsgset
        # split, this review is more needed.
        current = POMsgSet.select('''
            POMsgSet.sequence > 0 AND
            POMsgSet.fuzzy = FALSE AND
            POTMsgSet.sequence > 0 AND
            POTMsgSet.primeMsgID = POMsgSet.primeMsgID AND
            POMsgSet.pofile = %d AND
            POTMsgSet.potemplate = POMsgSet.potemplate
            ''' % self.id, clauseTables=('POTMsgSet',)).count()
        updates = POMsgSet.select('''
            POMsgSet.sequence > 0 AND
            POMsgSet.fuzzy = FALSE AND
            POTMsgSet.sequence > 0 AND
            POTMsgSet.primeMsgID = POMsgSet.primeMsgID AND
            POMsgSet.pofile = %d AND
            POTMsgSet.potemplate = POMsgSet.potemplate AND
            FileSighting.pomsgset = POMsgSet.id AND
            RosettaSighting.pomsgset = POMsgSet.id AND
            FileSighting.inLastRevision = TRUE AND
            RosettaSighting.inLastRevision = FALSE AND
            FileSighting.active = TRUE AND
            RosettaSighting.active = TRUE AND
            RosettaSighting.dateLastActive > FileSighting.dateLastActive
            ''' % self.id, clauseTables=(
                                         'POMsgSet PotSet',
                                         'POTranslationSighting FileSighting',
                                         'POTranslationSighting RosettaSighting',
                                        )).count()
        rosetta = POMsgSet.select('''
            POMsgSet.fuzzy = FALSE AND
            PotSet.sequence > 0 AND
            PotSet.primeMsgID = POMsgSet.primeMsgID AND
            POMsgSet.pofile = %d AND
            PotSet.potemplate = POMsgSet.potemplate AND
            PotSet.pofile IS NULL AND
            (SELECT COUNT(*) from
              POTranslationSighting POSighting WHERE
              POSighting.POMsgSet = POMsgSet.id AND
              POSighting.active = TRUE AND
              POSighting.inLastRevision = TRUE) = 0 AND
            (SELECT COUNT(*) from
              POTranslationSighting RosettaSighting WHERE
              RosettaSighting.POMsgSet = POMsgSet.id AND
              RosettaSighting.active = TRUE) > 0
            ''' % self.id, clauseTables=(
                                         'POMsgSet PotSet',
                                        )).count()
        self.set(currentCount=current,
                 updateCount=updates,
                 rosettaCount=rosetta)
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


class POMsgSet(SQLBase):
    implements(IEditPOMsgSet)

    _table = 'POMsgSet'

    _columns = [
        IntCol(name='sequence', dbName='sequence', notNull=True),
        ForeignKey(name='pofile', foreignKey='POFile', dbName='pofile',
            notNull=True),
        BoolCol(name='iscomplete', dbName='iscomplete', notNull=True),
        BoolCol(name='obsolete', dbName='obsolete', notNull=True),
        BoolCol(name='fuzzy', dbName='fuzzy', notNull=True),
        StringCol(name='commenttext', dbName='commenttext', notNull=False,
            default=None),
        ForeignKey(name='potmsgset', foreignKey='POTMsgSet',
            dbName='potmsgset', notNull=True),
    ]


    def pluralForms(self):
        if self.potmsgset.messageIDs().count() > 1:
            # has plurals
            return self.pofile.pluralforms
        else:
            # message set is singular
            return 1

    def translations(self):
        pluralforms = self.pluralForms()
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

    def makeTranslationSighting(self, person, text, pluralForm,
                              update=False, fromPOFile=False):
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

            if not update:
                raise KeyError(
                    "There is already a translation sighting for this "
                    "message set, text, plural form and person.")

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
                origin=origin,
                # XXX: FIXME
                license=1)

        # Make all other sightings inactive.

        self._connection.query(
            '''
            UPDATE POTranslationSighting SET active = FALSE
            WHERE
                pomsgset = %d AND
                pluralform = %d AND
                id <> %d
            ''' % (self.id, pluralForm, sighting.id))

        return sighting


class POTranslationSighting(SQLBase):
    implements(IPOTranslationSighting)

    _table = 'POTranslationSighting'

    _columns = [
        ForeignKey(name='pomsgset', foreignKey='POMsgSet', dbName='pomsgset',
            notNull=True),
        ForeignKey(name='potranslation', foreignKey='POTranslation',
            dbName='potranslation', notNull=True),
#        ForeignKey(name='license', foreignKey='License', dbName='license',
#            notNull=True),
        IntCol(name='license', dbName='license', notNull=True),
        DateTimeCol(name='datefirstseen', dbName='datefirstseen',
            notNull=True),
        DateTimeCol(name='datelastactive', dbName='datelastactive',
            notNull=True),
        BoolCol(name='inlastrevision', dbName='inlastrevision', notNull=True),
        IntCol(name='pluralform', dbName='pluralform', notNull=True),
        BoolCol(name='active', dbName='active', notNull=True, default=DEFAULT),
        # See canonical.lp.dbschema.RosettaTranslationOrigin.
        IntCol(name='origin', dbName='origin', notNull=True),
        ForeignKey(name='person', foreignKey='Person', dbName='person',
            notNull=True),
    ]


class POTranslation(SQLBase):
    implements(IPOTranslation)

    _table = 'POTranslation'

    _columns = [
        StringCol(name='translation', dbName='translation', notNull=True,
            unique=True, alternateID=True)
    ]

