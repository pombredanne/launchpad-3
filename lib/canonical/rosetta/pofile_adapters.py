from ipofile import IPOHeader, IPOMessage
from pofile import POHeader, POMessage, POParser
from interfaces import IPOMessageSet
from zope.interface import implements
import sets

# This file raises string exceptions.  These should be considered
# "XXX FIXME" markings - as in, replace these with whatever real
# exception should be raised in each case.

class DatabaseConstraintError(Exception):
    pass


class WatchedSet(sets.Set):
    """ Mutable set class that "warns" a callable when changed."""

    __slots__ = ['_watcher']

    def __init__(self, watcher, iterable=None):
        """Construct a set from an optional iterable."""
        self._data = {}
        self._watcher = watcher
        if iterable is not None:
            self._update(iterable)

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

    # FIXME: this list implementation is incomplete.  Dude, if you want to do
    # del foo.msgstrs[2]
    # or
    # foo.msgstrs.pop()
    # then you're probably on crack anyway.

    def __setitem__(self, index, value):
        current = self._msgset.getTranslationSighting(index)
        if value == current.poTranslation.text:
            return
        current.setCurrent(False)
        new = self._msgset.makeTranslationSighting(value, index)

    def __getitem__(self, index):
        return self._msgset.getTranslationSighting(index).poTranslation.text


class MessageProxy(POMessage):
    implements(IPOMessage)

    def __init__(self, msgset):
        self._msgset = msgset

    def _get_msgid(self):
        return self._msgset.primeMessageID_.text
    def _set_msgid(self):
        raise DatabaseConstraintError("The primary message ID of a messageset can't be changed"
                                      " once it's in the database.  Create a new messageset"
                                      " instead.")
    msgid = property(_get_msgid, _set_msgid)

    def _get_msgidPlural(self):
        msgids = self._msgset.messageIDs()
        if msgids.count() >= 2:
            return msgids[1]
        return None
    def _set_msgidPlural(self, value):
        # do we already have one?
        old_plural = self.msgidPlural
        if old_plural is not None:
            old_plural = self._msgset.getMessageIDSighting(1)
            old_plural.setCurrent(False)
        self._msgset.makeMessageIDSighting(value, 1)
    msgidPlural = property(_get_msgidPlural)

    def _get_msgstr(self):
        translations = self._msgset.translations()
        if translations.count() == 1:
            return translations[0].text
    def _set_msgstr(self, value):
        current = self._msgset.getTranslationSighting(0)
        if value == current.poTranslation.text:
            return
        current.setCurrent(False)
        new = self._msgset.makeTranslationSighting(0, index)        
    msgstr = property(_get_msgstr)

    def _get_msgstrPlurals(self):
        translations = self._msgset.translations()
        if translations.count() > 1:
            # test is necessary because the interface says when
            # there are no plurals, msgstrPlurals is None
            return TranslationsList(self._msgset)
    def _set_msgstrPlurals(self, value):
        current = self.msgstrPlurals
        if len(value) != len(current):
            raise ValueError("New list of message strings has different size as current one")
        for index, item in enumerate(value):
            current[index] = item
    msgstrPlurals = property(_get_msgstrPlurals)

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
        return WatchedSet(
            self._set_flags,
            [flag.strip() for flag in self._msgset.flagsComment.split(',')]
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
            # bitch like crazy
            raise 'something'

    def __call__(self, msgid, **kw):
        "Instantiate a single message/messageset"
        try:
            msgset = self.potemplate[msgid]
        except KeyError:
            msgset = self.potemplate.newMessageSet(msgid)
        if msgset is None:
            msgset = potemplate.newMessageSet(msgid)
        else:
            msgset.getMessageIDSighting(0).touch()
        self.len += 1
        msgset.sequence = self.len
        proxy = MessageProxy(msgset)
        proxy.msgidPlural = kw.get('msgidPlural', '')
        if kw.get('msgstr'):
            # if not is_it_the_header:
            #    raise "You're on crack."
            proxy.msgstr = kw['msgstr']
        proxy.commentText = kw.get('commentText', '')
        proxy.sourceComment = kw.get('sourceComment', '')
        proxy.fileReferences = kw.get('fileReferences', '').strip()
        proxy.flags = kw.get('flags', ())
        if kw.get('msgstrPlurals'):
            raise "You're on crack."
        proxy.obsolete = kw.get('obsolete', False)


class POFileImporter(object):
    def __init__(self, potemplate, changeset):
        raise NotImplementedError
        self.potemplate = potemplate
        self.changeset = changeset # are we going to use this?
        self.len = 0
        self.parser = POParser(translation_factory=self)

    def doImport(self, filelike):
        "Import a file (or similar object)"
        self.potemplate.expireAllMessages()
        # what policy here? small bites? lines? how much memory do we want to eat?
        parser.write(filelike.read())
        parser.finish()
        if not parser.header:
            # bitch like crazy
            raise 'something'

    def __call__(self, msgid, **kw):
        "Instantiate a single message/messageset"
        msgset = self.potemplate[msgid]
        if msgset is None:
            msgset = potemplate.newMessageSet(msgid)
        else:
            msgset.getMessageIDSighting(0).touch()
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
