# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: F2FF38E7-F84C-11D8-AC8B-000A95A06FC6

from zope.interface import implements
from zope.schema.interfaces import IVocabulary, IVocabularyTokenized
from zope.schema.vocabulary import SimpleTerm

from canonical.database.doap import Sourcepackage, Product

__metaclass__ = type

class NamedTableVocabulary(object):
    implements(IVocabulary, IVocabularyTokenized)
    def __init__(self, context):
        self.context = context

    def _toTerm(self, pkg):
        return SimpleTerm(pkg.id, pkg.name, pkg.title)

    def __iter__(self):
        for pkg in self._table.select(orderBy='name'):
            yield self._toTerm(pkg)

    def __len__(self):
        return len(iter(self))

    def __contains__(self, key):
        pkgs = list(self._table.select(self._table.q.id == key))
        if len(pkgs) > 0:
            return True
        return False

    def getQuery(self):
        return None

    def getTerm(self, value):
        pkgs = list(self._table.select(id=value))
        if len(pkgs) == 0:
            raise LookupError, value
        return self._toTerm(pkgs[0])

    def getTermByToken(self, token):
        pkgs = list(self._table.select(self._table.q.name == token))
        if len(pkgs) == 0:
            raise LookupError, value
        return self._toTerm(pkgs[0])

class SourcepackageVocabulary(NamedTableVocabulary):
    _table = Sourcepackage

class ProductVocabulary(NamedTableVocabulary):
    _table = Product


