# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: F2FF38E7-F84C-11D8-AC8B-000A95A06FC6

from zope.interface import implements
from zope.schema.interfaces import IVocabulary, IVocabularyTokenized
from zope.schema.vocabulary import SimpleTerm

from canonical.database.foaf import Person
from canonical.database.doap import Sourcepackage, Product, Binarypackage
from canonical.database.malone import BugSystem

__metaclass__ = type

# TODO: These vocabularies should limit their choices based on context (?)

class TitledTableVocabulary(object):
    implements(IVocabulary, IVocabularyTokenized)
    _orderBy = 'name'
    def __init__(self, context):
        self.context = context

    def _toTerm(self, pkg):
        return SimpleTerm(pkg.id, pkg.name, pkg.title)

    def __iter__(self):
        for pkg in self._table.select(orderBy=self._orderBy):
            yield self._toTerm(pkg)

    def __len__(self):
        return len(iter(self))

    def __contains__(self, key):
        try:
            pkgs = list(self._table.select(self._table.q.id == int(key)))
            if len(pkgs) > 0:
                return True
        except ValueError:
            pass
        return False

    def getQuery(self):
        return None

    def getTerm(self, value):
        try:
            pkgs = list(self._table.select(self._table.q.id==int(value)))
        except ValueError:
            raise LookupError, value
        if len(pkgs) == 0:
            raise LookupError, value
        return self._toTerm(pkgs[0])

    def getTermByToken(self, token):
        try:
            pkgs = list(self._table.select(self._table.q.name==token))
        except ValueError:
            raise LookupError, value
        if len(pkgs) == 0:
            raise LookupError, value
        return self._toTerm(pkgs[0])

class SourcepackageVocabulary(TitledTableVocabulary):
    _table = Sourcepackage

class ProductVocabulary(TitledTableVocabulary):
    _table = Product

# We cannot refer to a Binarypackage unambiguously by a name, as
# we have no assurace that a generated name using $BinarypackageName.name
# and $Binarypackage.version will be unique
# TODO: The edit sourcepackagebugassignment for does not default its
# binary package field
class BinarypackageVocabulary(TitledTableVocabulary):
    _table = Binarypackage
    _orderBy = 'id'
    def _toTerm(self, pkg):
        return SimpleTerm(pkg.id, str(pkg.id), pkg.title)

    def getTermByToken(self, token):
        return self.getTerm(token)

class BugSystemVocabulary(TitledTableVocabulary):
    _table = BugSystem

class PersonVocabulary(TitledTableVocabulary):
    _table = Person
    _orderBy = 'familyname'
    def _toTerm(self, pkg):
        return SimpleTerm(
                pkg.id, str(pkg.id), pkg.displayname or '%s %s' % (
                    pkg.givenname, pkg.familyname
                    )
                )
    def getTermByToken(self, token):
        return self.getTerm(token)
