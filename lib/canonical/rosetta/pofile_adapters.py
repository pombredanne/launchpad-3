from ipofile import IPOHeader, IPOMessage
from pofile import POHeader, POMessage, POParser, POInvalidInputError
from zope.interface import implements
import sets

class DatabaseConstraintError(Exception):
    pass


# XXX: not using Person at all yet
class FakePerson(object):
    id = 1
XXXperson = FakePerson()

# XXX: if you *modify* the adapted pofile "object", it assumes you're updating
#      it from the latest revision (for the purposes of inLatestRevision fields).
#      That should probably be optional.


class WatchedSet(sets.Set):
    """ Mutable set class that "warns" a callable when changed."""

    __slots__ = ['_watcher']

    def __init__(self, watcher, iterable=None):
        """Construct a set from an optional iterable."""
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
    def __init__(self, messageset):
        self._msgset = messageset
        # cache, as we use that value a lot
        self._nplurals = messageset.nplurals()

    # FIXME: this list implementation is incomplete.  Dude, if you want to do
    # del foo.msgstrs[2]
    # or
    # foo.msgstrs.pop()
    # then you're probably on crack anyway.

    def __setitem__(self, index, value):
        if not value:
            if self._msgset.poFile is None:
                # template
                return
            try:
                sighting = self._msgset.getTranslationSighting(index, allowOld=True)
            except IndexError:
                # nothing passed, nothing in the DB, then it's ok
                return
            sighting.inLatestRevision = False
        if index > self._nplurals:
            raise IndexError, index
        if self._msgset.poFile is None:
            # template
            raise pofile.POSyntaxError(msg="PO Template has translations!")
        self._msgset.makeTranslationSighting(XXXperson, value, index,
                                             update=True, fromPOFile=True)

    def __getitem__(self, index):
        try:
            return self._msgset.getTranslationSighting(index, allowOld=True).poTranslation.translation
        except KeyError:
            if index < self._nplurals:
                return ''
            raise IndexError, index

    def __len__(self):
        return self._msgset.translations().count()

    def append(self, value):
        if len(self) >= self._nplurals:
            raise ValueError, "Too many plural forms"
        self._msgset.makeTranslationSighting(XXXperson, value, len(self),
                                             update=True, fromPOFile=True)


class MessageProxy(POMessage):
    implements(IPOMessage)

    def __init__(self, msgset):
        self._msgset = msgset
        self._translations = TranslationsList(msgset)

    def _get_msgid(self):
        return self._msgset.primeMessageID_.msgid
    def _set_msgid(self):
        raise DatabaseConstraintError("The primary message ID of a messageset can't be changed"
                                      " once it's in the database.  Create a new messageset"
                                      " instead.")
    msgid = property(_get_msgid, _set_msgid)

    def _get_msgidPlural(self):
        msgids = self._msgset.messageIDs()
        if msgids.count() >= 2:
            return msgids[1].msgid
        return None
    def _set_msgidPlural(self, value):
        # do we already have one?
        old_plural = self.msgidPlural
        if old_plural is not None:
            old_plural = self._msgset.getMessageIDSighting(1)
            old_plural.inPOFile = False
        self._msgset.makeMessageIDSighting(value, 1, update=True)
    msgidPlural = property(_get_msgidPlural, _set_msgidPlural)

    def _get_msgstr(self):
        translations = list(self._msgset.translations())
        if len(translations) == 1:
            return translations[0].translation
    def _set_msgstr(self, value):
        # let's avoid duplication of code
        self._translations[0] = value
    msgstr = property(_get_msgstr, _set_msgstr)

    def _get_msgstrPlurals(self):
        translations = list(self._msgset.translations())
        if len(translations) > 1:
            # test is necessary because the interface says when
            # there are no plurals, msgstrPlurals is None
            return self._translations
    def _set_msgstrPlurals(self, value):
        for index, item in enumerate(value):
            self._translations[index] = item
    msgstrPlurals = property(_get_msgstrPlurals, _set_msgstrPlurals)

    def _get_commentText(self):
        return self._msgset.commentText
    def _set_commentText(self, value):
        self._msgset.commentText = value
    commentText = property(_get_commentText, _set_commentText)

    def _get_sourceComment(self):
        return self._msgset.sourceComment
    def _set_sourceComment(self, value):
        self._msgset.sourceComment = value
    sourceComment = property(_get_sourceComment, _set_sourceComment)

    def _get_fileReferences(self):
        return self._msgset.fileReferences
    def _set_fileReferences(self, value):
        self._msgset.fileReferences = value
    fileReferences = property(_get_fileReferences, _set_fileReferences)

    def _get_flags(self):
        flags = self._msgset.flagsComment or ''
        return WatchedSet(
            self._set_flags,
            [flag.strip() for flag in flags.split(',')]
            )
    def _set_flags(self, value):
        self._msgset.flagsComment = self.flagsText(value, withHash=False)
    flags = property(_get_flags, _set_flags)

    def _get_obsolete(self):
        return self._msgset.obsolete
    def _set_obsolete(self, value):
        self._msgset.obsolete = value
    obsolete = property(_get_obsolete, _set_obsolete)


class TemplateImporter(object):
    def __init__(self, potemplate, changeset):
        self.potemplate = potemplate
        self.changeset = changeset # are we going to use this?
        self.len = 0
        self.parser = POParser(translation_factory=self)

    def doImport(self, filelike):
        "Import a file (or similar object)"
        self.potemplate.expireAllMessages()
        # what policy here? small bites? lines? how much memory do we want to eat?
        self.parser.write(filelike.read())
        self.parser.finish()
        if not self.parser.header:
            raise POInvalidInputError('PO template has no header', 0)

    def __call__(self, msgid, **kw):
        "Instantiate a single message/messageset"
        try:
            msgset = self.potemplate[msgid]
        except KeyError:
            msgset = self.potemplate.makeMessageSet(msgid, update=True)
        else:
            try:
                msgset.getMessageIDSighting(0, allowOld=True).dateLastSeen = "NOW"
            except KeyError:
                # If we don't have any MessageIDSighting, we shouldn't fail.
                pass
        self.len += 1
        msgset.sequence = self.len
        proxy = MessageProxy(msgset)
        proxy.msgidPlural = kw.get('msgidPlural', '')
        if kw.get('msgstr'):
            raise POInvalidInputError('PO template has msgstrs', 0)
        proxy.commentText = kw.get('commentText', '')
        proxy.sourceComment = kw.get('sourceComment', '')
        proxy.fileReferences = kw.get('fileReferences', '').strip()
        proxy.flags = kw.get('flags', ())
        plurals = []
        for inp_plural in kw.get('msgstrPlurals', ()):
            if inp_plural:
                raise POInvalidInputError('PO template has msgstrs', 0)
            plurals.append(inp_plural)
        proxy.msgstrPlurals = plurals
        proxy.obsolete = kw.get('obsolete', False)
        return proxy


class POFileImporter(object):
    def __init__(self, pofile, changeset):
        self.pofile = pofile
        self.changeset = changeset # are we going to use this?
        self.len = 0
        self.parser = POParser(translation_factory=self)

    def doImport(self, filelike):
        "Import a file (or similar object)"
        self.pofile.expireAllMessages()
        # what policy here? small bites? lines? how much memory do we want to eat?
        self.parser.write(filelike.read())
        self.parser.finish()
        if not self.parser.header:
            raise POInvalidInputError('PO file has no header', 0)
        self.pofile.set(
            topComment=self.parser.header.commentText.encode('utf-8'),
            header=self.parser.header.msgstr.encode('utf-8'),
            headerFuzzy='fuzzy' in self.parser.header.flags,
            pluralforms=self.parser.header.nplurals)

    def __call__(self, msgid, **kw):
        "Instantiate a single message/messageset"
        try:
            msgset = self.pofile[msgid]
        except KeyError:
            msgset = self.pofile.poTemplate.makeMessageSet(msgid, self.pofile, update=True)
        else:
            msgset.getMessageIDSighting(0, allowOld=True).dateLastSeen = "NOW"
        self.len += 1
        msgset.sequence = self.len
        proxy = MessageProxy(msgset)
        proxy.msgidPlural = kw.get('msgidPlural', '')
        if kw.get('msgstr'):
            proxy.msgstr = kw['msgstr']
        proxy.commentText = kw.get('commentText', '')
        proxy.sourceComment = kw.get('sourceComment', '')
        proxy.fileReferences = kw.get('fileReferences', '').strip()
        proxy.flags = kw.get('flags', ())
        if kw.get('msgstrPlurals'):
            proxy.msgstrPlurals = kw['msgstrPlurals']
        proxy.obsolete = kw.get('obsolete', False)
        return proxy
