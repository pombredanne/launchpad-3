from ipofile import IPOHeader, IPOMessage
from pofile import POHeader, POMessage
from interfaces import IPOMessageSet
from zope.interface import implements
import sets

class DatabaseConstraintError(Exception):
    pass


class WatchedSet(sets.Set):
    """ Mutable set class that "warns" a callable when changed."""

    __slots__ = ['_watcher']

    # BaseSet + operations requiring mutability; no hashing

    def __init__(self, watcher, iterable=None):
        """Construct a set from an optional iterable."""
        self._data = {}
        self._watcher = watcher
        if iterable is not None:
            self._update(iterable)

    def _update(self, iterable):
        sets.Set._update(self, iterable)
        self.watcher(self)

    def __ior__(self, other):
        sets.Set.__ior__(self, other)
        self.watcher(self)

    def __iand__(self, other):
        sets.Set.__iand__(self, other)
        self.watcher(self)

    def intersection_update(self, other):
        sets.Set.intersection_update(self, other)
        self.watcher(self)

    def symmetric_difference_update(self, other):
        sets.Set.symmetric_difference_update(self, other)
        self.watcher(self)

    def difference_update(self, other):
        sets.Set.difference_update(self, other)
        self.watcher(self)

    def clear(self):
        sets.Set.clear(self)
        self.watcher(self)

    def add(self, element):
        sets.Set.add(self, element)
        self.watcher(self)

    def remove(self, element):
        sets.Set.remove(self, element)
        self.watcher(self)

    def pop(self):
        sets.Set.pop(self)
        self.watcher(self)


class MessageProxy(POMessage):
    implements (IPOMessage)

    def __init__(self, msgset):
        self._msgset = msgset

    def _get_msgid(self):
        return self._msgset.primeMessageID
    def _set_msgid(self):
        raise DatabaseConstraintError("The primary message ID of a messageset can't be changed"
                                      " once it's in the database.  Create a new messageset"
                                      " instead.")
    msgid = property(_get_msgid, _set_msgid)

    def _get_msgidPlural(self):
        msgids = self._msgset.messageIDs()
        if len(msgids) >= 2:
            return msgids[1]
        return None
    # XXX: setter (gonna be complicated)
    msgidPlural = property(_get_msgidPlural)

    def _get_msgstr(self):
        translations = self._msgset.translations()
        if len(translations) == 1:
            return translations[0]
    # XXX: setter (gonna be complicated)
    msgstr = property(_get_msgstr)

    def _get_msgstrPlurals(self):
        translations = self._msgset.translations()
        if len(translations) > 1:
            return translations
    # XXX: setter (gonna be complicated)
    msgstrPlurals = property(_get_msgstrPlurals)

    def _get_commentText(self):
        return self._msgset.commentText
    def _set_commentText(self, value):
        self._msgset.commentText = value
    commentText = property(_get_commentText, _set_commentText)

    def _get_generatedComment(self):
        return self._msgset.generatedComment
    def _set_generatedComment(self, value):
        self._msgset.generatedComment = value
    generatedComment = property(_get_generatedComment, _set_generatedComment)

    def _get_fileReferences(self):
        return self._msgset.fileReferences
    def _set_fileReferences(self, value):
        self._msgset.fileReferences = value
    fileReferences = property(_get_fileReferences, _set_fileReferences)

    def _get_flags(self):
        return sets.WatchedSet(
            self._set_flags,
            [flag.strip() for flag in self._msgset.flagsComment.split(',')]
            )
    def _set_flags(self, value):
        self._msgset.flagsComment = self.flagsText(value)
    flags = property(_get_flags, _set_flags)

    def _get_obsolete(self):
        return self._msgset.obsolete
    def _set_obsolete(self, value):
        self._msgset.obsolete = value
    obsolete = property(_get_obsolete, _set_obsolete)

