# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Vocabularies pulling stuff from the database.

You probably don't want to use these classes directly - see the
docstring in __init__.py for details.
"""

__metaclass__ = type

__all__ = [
    'IHugeVocabulary',
    'SQLObjectVocabularyBase',
    'NamedSQLObjectVocabulary',
    'NamedSQLObjectHugeVocabulary',
    'sortkey_ordered_vocab_factory',
    'vocab_factory'
]

import operator

from sqlobject import AND, CONTAINSSTRING
from sqlos.interfaces import ISelectResults

from zope.interface import implements, Attribute
from zope.schema.interfaces import IVocabulary, IVocabularyTokenized
from zope.schema.vocabulary import SimpleTerm
from zope.security.proxy import isinstance as zisinstance
from zope.schema.vocabulary import SimpleVocabulary

from canonical.database.sqlbase import SQLBase


class IHugeVocabulary(IVocabulary, IVocabularyTokenized):
    """Interface for huge vocabularies.

    Items in an IHugeVocabulary should have human readable tokens or the
    default UI will suck.
    """

    displayname = Attribute(
        'A name for this vocabulary, to be displayed in the popup window.')

    def searchForTerms(query=None):
        """Return an iterable of SimpleTerms that match the search string.

        The iterable must have a count() method.

        Note that what is searched and how the match is the choice of the
        IHugeVocabulary implementation.
        """


class CountableIterator:
    """Implements a wrapping iterator with a count() method.

    This iterator implements a subset of the ISelectResults interface;
    namely the portion required to have it work as part of a
    BatchNavigator.
    """

    def __init__(self, count, iterator, item_wrapper):
        """Construct a CountableIterator instance.

        Arguments:
            - count: number of items in the iterator
            - iterator: the iterable we wrap
            - item_wrapper: a callable that will be invoked for each
              item we return.
        """
        self._count = count
        self._iterator = iterator
        self._item_wrapper = item_wrapper

    def count(self):
        """Return the number of items in the iterator."""
        return self._count

    def __iter__(self):
        for item in self._iterator:
            yield self._item_wrapper(item)

    def __getitem__(self, arg):
        # This is actually required because BatchNavigator will attempt
        # to slice into us; we just pass on the buck.
        for item in self._iterator[arg]:
            yield self._item_wrapper(item)

    def __len__(self):
        # XXX: __len__ is required to make BatchNavigator work; we
        # should probably change that to either check for the presence
        # of a count() method, or for a simpler interface than
        # ISelectResults, but I'm not going to do that today.
        #   -- kiko, 2006-01-16
        return self._count


class SQLObjectVocabularyBase:
    """A base class for widgets that are rendered to collect values
    for attributes that are SQLObjects, e.g. ForeignKey.

    So if a content class behind some form looks like:

    class Foo(SQLObject):
        id = IntCol(...)
        bar = ForeignKey(...)
        ...

    Then the vocabulary for the widget that captures a value for bar
    should derive from SQLObjectVocabularyBase.
    """
    implements(IVocabulary, IVocabularyTokenized)
    _orderBy = None
    _filter = None

    def __init__(self, context=None):
        self.context = context

    # XXX: note that the method searchForTerms is part of
    # IHugeVocabulary, and so should not necessarily need to be
    # implemented here; however, many of our vocabularies depend on
    # searchForTerms for popup functionality so I have chosen to just do
    # that. It is possible that a better solution would be to have the
    # search functionality produce a new vocabulary restricted to the
    # desired subset. -- kiko, 2006-01-16
    def searchForTerms(self, query=None):
        results = self.search(query)
        return CountableIterator(results.count(), results, self.toTerm)

    def search(self):
        # This default implementation of searchForTerms glues together
        # the legacy API of search() with the toTerm method. If you
        # don't reimplement searchForTerms you will need to at least
        # provide your own search() method.
        raise NotImplementedError

    def toTerm(self, obj):
        # This default implementation assumes that your object has a
        # title attribute. If it does not you will need to reimplement
        # toTerm, or reimplement the whole searchForTerms.
        return SimpleTerm(obj, obj.id, obj.title)

    def __iter__(self):
        """Return an iterator which provides the terms from the vocabulary."""
        params = {}
        if self._orderBy:
            params['orderBy'] = self._orderBy
        for obj in self._table.select(self._filter, **params):
            yield self.toTerm(obj)

    def __len__(self):
        return len(list(iter(self)))

    def __contains__(self, obj):
        # Sometimes this method is called with an SQLBase instance, but
        # z3 form machinery sends through integer ids. This might be due
        # to a bug somewhere.
        if zisinstance(obj, SQLBase):
            clause = self._table.q.id == obj.id
            if self._filter:
                # XXX: this code is untested -- kiko, 2006-01-16
                clause = AND(clause, self._filter)
            found_obj = self._table.selectOne(clause)
            return found_obj is not None and found_obj == obj
        else:
            clause = self._table.q.id == int(obj)
            if self._filter:
                # XXX: this code is untested -- kiko, 2006-01-16
                clause = AND(clause, self._filter)
            found_obj = self._table.selectOne(clause)
            return found_obj is not None

    def getQuery(self):
        return None

    def getTerm(self, value):
        # Short circuit. There is probably a design problem here since
        # we sometimes get the id and sometimes an SQLBase instance.
        if zisinstance(value, SQLBase):
            return self.toTerm(value)

        try:
            value = int(value)
        except ValueError:
            raise LookupError(value)

        clause = self._table.q.id == value
        if self._filter:
            clause = AND(clause, self._filter)
        try:
            obj = self._table.selectOne(clause)
        except ValueError:
            raise LookupError(value)

        if obj is None:
            raise LookupError(value)

        return self.toTerm(obj)

    def getTermByToken(self, token):
        return self.getTerm(token)

    def emptySelectResults(self):
        """Return a SelectResults object without any elements.

        This is to be used when no search string is given to the search()
        method of subclasses, in order to be consistent and always return
        a SelectResults object.
        """
        return self._table.select('1 = 2')


class NamedSQLObjectVocabulary(SQLObjectVocabularyBase):
    """A SQLObjectVocabulary base for database tables that have a unique
    *and* ASCII name column.

    Provides all methods required by IHugeVocabulary, although it
    doesn't actually specify this interface since it may not actually
    be huge and require the custom widgets.

    May still want to override toTerm to provide a nicer title and
    search to search on titles or descriptions.
    """
    _orderBy = 'name'

    def toTerm(self, obj):
        return SimpleTerm(obj.id, obj.name, obj.name)

    def getTermByToken(self, token):
        clause = self._table.q.name == token
        if self._filter:
            clause = AND(clause, self._filter)
        objs = list(self._table.select(clause))
        if not objs:
            raise LookupError(token)
        return self.toTerm(objs[0])

    def search(self, query):
        """Return terms where query is a subtring of the name."""
        if query:
            clause = CONTAINSSTRING(self._table.q.name, query)
            if self._filter:
                clause = AND(clause, self._filter)
            return self._table.select(clause, orderBy=self._orderBy)
        return self.emptySelectResults()


class NamedSQLObjectHugeVocabulary(NamedSQLObjectVocabulary):
    """A NamedSQLObjectVocabulary that implements IHugeVocabulary."""

    implements(IHugeVocabulary)
    _orderBy = 'name'
    displayname = None

    def __init__(self, context=None):
        NamedSQLObjectVocabulary.__init__(self, context)
        if self.displayname is None:
            self.displayname = 'Select %s' % self.__class__.__name__


# TODO: Make DBSchema classes provide an interface, so we can adapt IDBSchema
# to IVocabulary
def vocab_factory(schema, noshow=[]):
    """Factory for IDBSchema -> IVocabulary adapters.

    This function returns a callable object that creates vocabularies
    from dbschemas.

    The items appear in value order, lowest first.
    """
    def factory(context, schema=schema, noshow=noshow):
        """Adapt IDBSchema to IVocabulary."""
        # XXX kiko: we should use sort's built-in DSU here.
        items = [(item.value, item.title, item)
            for item in schema.items
            if item not in noshow]
        items.sort()
        items = [(title, value) for sortkey, title, value in items]
        return SimpleVocabulary.fromItems(items)
    return factory

def sortkey_ordered_vocab_factory(schema, noshow=[]):
    """Another factory for IDBSchema -> IVocabulary.

    This function returns a callable object that creates a vocabulary
    from a dbschema ordered by that schema's sortkey.
    """
    def factory(context, schema=schema, noshow=noshow):
        """Adapt IDBSchema to IVocabulary."""
        items = [(item.title, item) for item in
                 sorted(schema.items, key=operator.attrgetter('sortkey'))
                 if item not in noshow]
        return SimpleVocabulary.fromItems(items)
    return factory
