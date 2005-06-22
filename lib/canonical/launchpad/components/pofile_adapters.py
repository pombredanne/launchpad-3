
# XXX: Carlos Perello Marin 2005-04-15: This code will be "componentized"
# soon. https://launchpad.ubuntu.com/malone/bugs/403


import sets
import warnings

from zope.interface import implements

from canonical.lp.dbschema import RosettaTranslationOrigin
from canonical.launchpad.interfaces import IPOHeader, IPOMessage
from canonical.launchpad.components.poparser import POHeader, POMessage, \
    POParser, POInvalidInputError
from canonical.launchpad.interfaces import IPOTemplate, IPOFile

class DatabaseConstraintError(Exception):
    pass
class UnknownUserError(Exception):
    pass


SINGULAR = 0
PLURAL = 1


class WatchedSet(sets.Set):
    """Mutable set class that "warns" a callable when changed."""
    # (Used for bridging flags/flagsComment)

    # need __slots__ because sets.Set says we do
    __slots__ = ['_watcher']

    def __init__(self, watcher, iterable=None):
        """Construct a set from an optional iterable.
        Watcher is called, with self as an argument, whenever
        our contents change."""
        self._data = {}
        self._watcher = watcher
        if iterable is not None:
            sets.Set._update(self, iterable)

    def _update(self, iterable):
        sets.Set._update(self, iterable)
        self._watcher(self)

    def __ior__(self, other):
        sets.Set.__ior__(self, other)
        self._watcher(self)

    def __iand__(self, other):
        sets.Set.__iand__(self, other)
        self._watcher(self)

    def intersection_update(self, other):
        sets.Set.intersection_update(self, other)
        self._watcher(self)

    def symmetric_difference_update(self, other):
        sets.Set.symmetric_difference_update(self, other)
        self._watcher(self)

    def difference_update(self, other):
        sets.Set.difference_update(self, other)
        self._watcher(self)

    def clear(self):
        sets.Set.clear(self)
        self._watcher(self)

    def add(self, element):
        sets.Set.add(self, element)
        self._watcher(self)

    def remove(self, element):
        sets.Set.remove(self, element)
        self._watcher(self)

    def pop(self):
        sets.Set.pop(self)
        self._watcher(self)


class TranslationsList(object):
    """Special list-like object to bridge translations.  It pretends to
    be a list of strings, but it actually fetches values from the database,
    using translation selections associated with the passed message set."""
    def __init__(self, messageset, person, published, is_editor):
        # message set we'll use to access the database
        self._msgset = messageset
        # a person - in case we need to create rows
        self._who = person
        # remember whether we are displaying / modifying the translations
        # that are active in rosetta, or that are published in the pofile
        self._published = published
        # remember whether or not the person making this submission has
        # permission to edit this pofile
        self._is_editor = is_editor
        # cache the number of plural forms, as we use that value a lot
        # find the correct number of forms - fortunately we
        # have a method that does just that
        self._nplurals = messageset.pluralforms

    # This list implementation is incomplete.  Dude, if you want to do
    # del foo.msgstrs[2]
    # or
    # foo.msgstrs.pop()
    # then you're probably on crack anyway.

    def __setitem__(self, index, value):
        """Set one single item. Index is the plural form"""
        # check that the plural form index makes sense
        if index >= self._nplurals:
            # Don't fail, just print a warning.
            warnings.warn("Found more pluralforms than expected "
                "for this language.")
        # if we don't have a Person instance, we can't create rows
        if self._who is None:
            raise UnknownUserError, \
                "Cannot create objects that have no Person"
        # create a translation submission
        self._msgset.makeSubmission(self._who, value, index,
            self._published, self._is_editor)

    def __getitem__(self, index):
        "one single item is being requested; index is the plural form"
        # first check if it is in the database
        submission =  self._msgset.activeSubmission(index)
        if submission is not None:
            return submission.potranslation.translation
        elif 0 <= index < self._nplurals:
            # it's not; but if it's a valid plural form, we should return
            # an empty string
            return ''
        # otherwise, raise an exception
        raise IndexError, index

    def __len__(self):
        """Return the number of translations expected."""
        return self._nplurals

    def append(self, value):
        """Add a new item at the end of the list"""
        # get the set of translations
        translations = self._msgset.active_texts
        # only valid if we're not already complete
        if translations[-1] is not None:
            raise ValueError, "Too many plural forms"
        # and if we have an associated Person object
        if self._who is None:
            raise UnknownUserError, \
                  "Tried to create objects but have no Person to associate with"
        # translations is a list like [ item1, ..., itemn, None, ..., None ]
        #  we want to set pluralform to the index of the first None
        # in the run of None's at the end of the list.  There may be
        # None's embedded in the run of items at the start of the list,
        # but they should be ignored so index() would give the wrong
        # answer
        pluralform = 0
        for index, tran in reversed(enumerate(translations)):
            if not tran:
                pluralform = index + 1
        if pluralform >= len(translations):
            raise ValueError, "No space left for extra translation"

        # create the translation submission
        self._msgset.makeSubmission(self._who, value, pluralform,
            self._published, self._is_editor)


class MessageProxy(POMessage):

    implements(IPOMessage)

    def __init__(self, potmsgset, published, is_editor, pomsgset=None,
        person=None, fuzzy=False):
        """Initialize a proxy.  We pretend to be a POMessage (and
        in fact shamelessly leech its methods), but our *data* is
        acquired from the database. The person object is used in case
        we need to create rows (for translations, sightings, etc)."""
        self._potmsgset = potmsgset
        self._pomsgset = pomsgset
        self._who = person
        self._published = published
        self._is_editor = is_editor
        self._fuzzy = fuzzy
        # create and store the TranslationsList object; since it's
        # fully dynamic, we can have a single one troughout our
        # lifetime
        if pomsgset:
            self._translations = TranslationsList(pomsgset, person,
                published, is_editor)

    # property: msgid
    # in rosetta: primeMessageID points to it
    def _get_msgid(self):
        return self._potmsgset.primemsgid_.msgid
    def _set_msgid(self):
        raise DatabaseConstraintError(
            "The primary message ID of a messageset can't be changed"
            " once it's in the database.  Create a new messageset"
            " instead.")
    msgid = property(_get_msgid, _set_msgid)

    # property: msgidPlural
    # in rosetta: messageIDs()[PLURAL] points to it
    def _get_msgidPlural(self):
        msgids = list(self._potmsgset.messageIDs())
        if len(msgids) >= 2:
            return msgids[PLURAL].msgid
        return None
    def _set_msgidPlural(self, value):
        # do we already have one?
        old_plural = self.msgidPlural
        if old_plural is not None:
            # yes; outdate it
            old_plural = self._potmsgset.getMessageIDSighting(PLURAL)
            old_plural.inPOFile = False
        # if value is empty or None, we don't need a sighting
        if value:
            # value is not empty; make a sighting for it
            # (or update an existing old sighting)
            self._potmsgset.makeMessageIDSighting(value, PLURAL, update=True)
    msgidPlural = property(_get_msgidPlural, _set_msgidPlural)

    # property: msgstr (pofile.py only uses that when it's not plural)
    # in rosetta: translations()[0] iif len(translations()) == 1
    def _get_msgstr(self):
        if self._pomsgset is None:
            return None
        translations = list(self._pomsgset.translations())
        if len(translations) == 1:
            return translations[SINGULAR]
    def _set_msgstr(self, value):
        # let's avoid duplication of code; TranslationsList has
        # all the code necessary to do this
        if self._pomsgset:
            self._translations[SINGULAR] = value
            # make sure we update statistics
            self._pomsgset.updateStatistics()
    msgstr = property(_get_msgstr, _set_msgstr)

    # property: msgstrPlurals (a list)
    # in rosetta: set of translations sightings that point back here
    # we use the helper class TranslationsList for both reading and writing
    def _get_msgstrPlurals(self):
        msgids = list(self._potmsgset.messageIDs())
        if len(msgids) > 1:
            # test is necessary because the interface says when
            # message is not plural, msgstrPlurals is None
            if self._pomsgset is None:
                return ('', '')
            return self._translations
    def _set_msgstrPlurals(self, value):
        if self._pomsgset:
            for index, item in enumerate(value):
                self._translations[index] = item
            # make sure we update statistics
            self._pomsgset.updateStatistics()
    msgstrPlurals = property(_get_msgstrPlurals, _set_msgstrPlurals)

    # property: commentText
    # in rosetta: commentText
    # pofile wants it to end in \n, rosetta wants it to *not* end in \n
    def _get_commentText(self):
        text = ''
        if self._potmsgset and self._potmsgset.commenttext:
            text = self._potmsgset.commenttext + '\n'
        if self._pomsgset and self._pomsgset.commenttext:
            text = text + self._pomsgset.commenttext + '\n'
        if text is not '':
            return text
        else:
            return None
    def _set_commentText(self, value):
        if value and value[-1] == '\n':
            value = value[:-1]
        if self._pomsgset is None:
            self._potmsgset.commenttext = value
        else:
            self._pomsgset.commenttext = value
    commentText = property(_get_commentText, _set_commentText)

    # property: sourceComment
    # in rosetta: sourceComment
    # pofile wants it to end in \n, rosetta wants it to *not* end in \n
    def _get_sourceComment(self):
        if not self._potmsgset.sourcecomment:
            return None
        return self._potmsgset.sourcecomment + '\n'
    def _set_sourceComment(self, value):
        if value and value[-1] == '\n':
            value = value[:-1]
        self._potmsgset.sourcecomment = value
    sourceComment = property(_get_sourceComment, _set_sourceComment)

    # property: fileReferences
    # in rosetta: fileReferences
    def _get_fileReferences(self):
        return self._potmsgset.filereferences
    def _set_fileReferences(self, value):
        self._potmsgset.filereferences = value
    fileReferences = property(_get_fileReferences, _set_fileReferences)

    # property: flags
    # in rosetta: flagsComment
    # this is the trickiest; pofile wants a set, rosetta wants a string
    # we use the helper class WatchedSet
    def _get_flags(self):
        flags = self._potmsgset.flagscomment or ''
        if flags:
            fl = [flag.strip() for flag in flags.split(',')]
        else:
            fl = []
        if self._published and self._pomsgset and self._pomsgset.publishedfuzzy:
            fl.append('fuzzy')
        elif not self._published and self._pomsgset and self._pomsgset.isfuzzy:
            fl.append('fuzzy')
        elif self._fuzzy and self._pomsgset and len(self._translations) > 1:
            # This fuzzy is added to let gettext handle better the incomplete
            # translations. It makes sense only with plural forms.
            for translation in self._translations:
                if not translation:
                    fl.append('fuzzy')
                    break
        return WatchedSet(self._set_flags, fl)
    def _set_flags(self, value):
        value = list(value)
        if 'fuzzy' in value:
            value.remove('fuzzy')
            # XXX: Carlos Perello Marin 15/10/04: I'm not sure if we should
            # remove the fuzzy flag if the pomsgset is None
            if self._pomsgset:
                if self._published:
                    self._pomsgset.publishedfuzzy = True
                else:
                    self._pomsgset.isfuzzy = True
        elif self._pomsgset:
            if self._published:
                self._pomsgset.publishedfuzzy = False
            else:
                self._pomsgset.isfuzzy = False
        self._potmsgset.flagscomment = self.flagsText(value, withHash=False)
    flags = property(_get_flags, _set_flags)

    # property: obsolete
    # in rosetta: obsolete
    # XXX: Carlos Perello Marin 15/10/04: We should only call this method
    # when we have a pomsgset.
    def _get_obsolete(self):
        return self._potmsgset.sequence == 0
    def _set_obsolete(self, value):
        if self._pomsgset:
            self._pomsgset.obsolete = value
    obsolete = property(_get_obsolete, _set_obsolete)


class TemplateImporter(object):
    "Importer object used for importing templates"
    __used_for__ = IPOTemplate

    # code that uses this will need to learn to set published and is_editor
    # correctly. PLEASE DO NOT set published=True or is_editor=False unless
    # you understand NonEditorTranslation and PoTranslationStorage
    def __init__(self, potemplate, person, published, is_editor):
        self.potemplate = potemplate
        # how many msgsets we already have; used for setting msgset.sequence
        self.len = 0
        self.person = person
        self.published = published
        self.is_editor = is_editor

    def doImport(self, filelike):
        """Import a file (or similar object)"""
        # each import, if an importer does more than one,
        # has to start with a fresh parser
        self.parser = POParser(translation_factory=self)
        # We should reset also the sequence number
        self.len = 0
        # mark all messages as not in file (sequence=0)
        self.potemplate.expireAllMessages()
        # XXX: what policy here? small bites? lines?
        # how much memory do we want to eat?
        self.parser.write(filelike.read())
        self.parser.finish()
        # update the statistics of each of the pofiles
        for pofile in self.potemplate.pofiles:
            pofile.updateStatistics()
        if self.parser.header is None:
            raise POInvalidInputError('PO template has no header', 0)
        # Store the .pot header into the database.
        self.potemplate.header = self.parser.header.msgstr.encode('utf-8')

    def __call__(self, msgid, **kw):
        """Instantiate a single message/messageset."""
        # first fetch the message set
        try:
            # is it already in the db?
            potmsgset = self.potemplate.messageSet(msgid)
        except KeyError:
            # no - create it
            potmsgset = self.potemplate.createMessageSetFromText(msgid)
        else:
            # it was in the db - update the timestamp
            potmsgset.getMessageIDSighting(SINGULAR, allowOld=True).dateLastSeen = "NOW"
        # set sequence
        self.len += 1
        potmsgset.sequence = self.len
        # create the proxy
        proxy = MessageProxy(potmsgset, self.published, self.is_editor,
            person=self.person)
        # capture all exceptions - we want (do we?) our IndexError, KeyError,
        # etc-s to become POInvalidInputError-s.
        try:
            # set (or unset) msgidPlural
            proxy.msgidPlural = kw.get('msgidPlural', None)
            # bark if we got translations
            if kw.get('msgstr'):
                raise POInvalidInputError('PO template has msgstrs', 0)
            # store comments
            proxy.commentText = kw.get('commentText', '')
            proxy.sourceComment = kw.get('sourceComment', '')
            proxy.fileReferences = kw.get('fileReferences', '').strip()
            proxy.flags = kw.get('flags', ())
            # if we got msgstrPlurals, just to be anal, check that it's
            # a list of empty strings; then set it
            plurals = []
            for inp_plural in kw.get('msgstrPlurals', ()):
                if inp_plural:
                    raise POInvalidInputError('PO template has msgstrs', 0)
                plurals.append(inp_plural)
            proxy.msgstrPlurals = plurals
            # set obsolete always to False in templates.
            proxy.obsolete = False
        except (KeyError, IndexError), e:
            raise POInvalidInputError(
                msg='Po file: invalid input on entry at line %d: %s'
                % (kw['_lineno'], str(e)))
        # Mao; return the results of our work
        return proxy


class POFileImporter(object):
    "Importer object used for importing PO files"
    __used_for__ = IPOFile

    # anything that uses this will need to learn how to use published and
    # is_editor correctly. PLEASE DO NOT do that until you understand
    # PoTranslationStorage and NonEditorTranslation fully
    def __init__(self, pofile, person, published, is_editor):
        self.pofile = pofile
        # how many msgsets we already have; used for setting msgset.sequence
        self.len = 0
        self.person = person
        self.header_stored = False
        # deal with cases where something was attached before we knew about
        # the difference between uploads and published ones
        if published is None:
            published = False
        self.published = published
        self.is_editor = is_editor

    def store_header(self):
        "Store the info about the header in the database"
        header = self.parser.header
        # if it's already stored, or not yet parsed, never mind
        if self.header_stored or not header:
            return
        # check that the plural forms info is valid
        if not header.nplurals:
            if self.pofile.pluralforms is not None:
                # first attempt: check if the database already knows it
                old_header = POHeader(msgstr=self.pofile.header)
                old_header.finish()
                header['plural-forms'] = old_header['plural-forms']
            elif self.pofile.language.pluralforms is not None:
                # Get the default value in the language database.
                header['plural-forms'] = self.pofile.language.pluralforms
            else:
                # we absolutely don't know it; only complain if
                # a plural translation is present
                header.pluralforms = 1
        # store it; use a single db operation. XXX sabdfl 27/05/05 should we
        # also differentiate between washeaderfuzzy and isheaderfuzzy?
        self.pofile.set(
            topcomment=header.commentText.encode('utf-8'),
            header=header.msgstr.encode('utf-8'),
            fuzzyheader='fuzzy' in header.flags,
            pluralforms=header.nplurals)
        # state that we've done so, or someone might give us a card
        self.header_stored = True

    def doImport(self, filelike):
        "Import a file (or similar object)"
        # each import, if an importer does more than one,
        # has to start with a fresh parser
        self.parser = POParser(translation_factory=self)
        # We should reset also the sequence number
        self.len = 0
        # mark all messages as not in file (sequence=0)
        self.pofile.expireAllMessages()
        # XXX: what policy here? small bites? lines?
        # how much memory do we want to eat?
        self.parser.write(filelike.read())
        self.parser.finish()
        # just in case file had 0 messages...
        self.store_header()
        if not self.header_stored:
            raise POInvalidInputError('PO file has no header', 0)
        # now we need to update the statistics of the pofile
        self.pofile.updateStatistics()


    def __call__(self, msgid, **kw):
        "Instantiate a single message/messageset"
        # check if we already stored the header, and if we haven't,
        # store it, so that msgset.pluralforms can return the
        # right thing
        self.store_header()
        # fetch the message set
        try:
            # is it already in the db?
            pomsgset = self.pofile.messageSet(msgid)
        except KeyError:
            # no - create it
            try:
                potmsgset = self.pofile.potemplate.messageSet(msgid)
            except KeyError:
                potmsgset = self.pofile.potemplate.createMessageSetFromText(msgid)
            pomsgset = self.pofile.createMessageSetFromMessageSet(potmsgset)
        # set sequence
        self.len += 1
        pomsgset.sequence = self.len
        # create the proxy
        proxy = MessageProxy(pomsgset.potmsgset, self.published,
            self.is_editor, pomsgset=pomsgset, person=self.person)
        # capture all exceptions - we want (do we?) our IndexError, KeyError,
        # etc-s to become POInvalidInputError-s.
        try:
            # set (or unset) msgidPlural
            proxy.msgidPlural = kw.get('msgidPlural', None)
            # if we got msgstr, then it's a singular; store it
            if 'msgstr' in kw:
                proxy.msgstr = kw['msgstr']
            # or was it plural?  In fact, store them all!
            if 'msgstrPlurals' in kw:
                proxy.msgstrPlurals = kw['msgstrPlurals']
            # store comments
            proxy.commentText = kw.get('commentText', '')
            proxy.sourceComment = kw.get('sourceComment', '')
            proxy.fileReferences = kw.get('fileReferences', '').strip()
            proxy.flags = kw.get('flags', ())
            # store obsolete
            proxy.obsolete = kw.get('obsolete', False)
        except (KeyError, IndexError), e:
            raise POInvalidInputError(
                msg='Po file: invalid input on entry at line %d: %s'
                % (kw['_lineno'], str(e)))
        # Mao; return the results of our work
        return proxy

