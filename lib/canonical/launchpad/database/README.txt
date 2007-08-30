Notes on using SQLObject
========================

SQLOS
-----

We inherit from sqlos.SQLOS rather than sqlobject.SQLObject, to get the Zope 3
glue that sqlos provides, e.g. per-thread connections.

Dealing with naming
-------------------

SQLObject's default naming "style" for translating Python names (such as
class and attribute names) to SQL names (such as table and column names) doesn't
match our SQL's naming scheme.  As a result, we can't simply say::

    class SourcePackageRelease(SQLOS):
        """A source package release."""

        version = StringCol()

Instead, we need to say::

    class SourcePackageRelease(SQLOS):
        """A source package release."""

        _table = 'SourcePackageRelease'
        name =  StringCol()

TODO: This should be fixable by defining our own style (see the sqlobject.styles
module).

Foreign Keys and Joins
----------------------

SQLObject also tries to guess names for foreign keys, but doesn't provide anyway
to hook that with its styles mechanism, so again we need to explicitly tell
SQLObject the names to use.  See this example::

    class Branch(SQLOS):
        """A specific branch in Arch (archive/category--branch--version)"""

        implements(IBranch)

        _table = 'branch'
        _idName = 'branch'
        description = StringCol(dbName='description')
        changesets = MultipleJoin('Changeset', joinColumn='branch')


    class Changeset(SQLOS):
        """A changeset"""

        implements(IChangeset)

        _table = 'changeset'
        _idName = 'changeset'
        branch = ForeignKey(foreignKey='Branch', dbName='branch',
                            notNull=True)
        message = StringCol(dbName='logmessage', notNull=True)

Note the passing of `name`, `foreignKey` and `dbName` to the ForeignKey column.

This example also demonstrates the MultipleJoin feature of SQLObject, which is
used for one-to-many relationships.  e.g.::

    Grab a random branch out of the DB
    >>> branch = Branch.select()[0]

    Grab that branch's changesets
    >>> changesets = branch.changesets

    A changeset's branch attribute gives us the original branch
    >>> changesets[0].branch is branch
    True

The string you pass to MultipleJoin is the name of another SQLOS subclass, as is
string passed as the `foreignKey` argument to ForeignKey (strings are used so
that you can reference a class that hasn't been declared yet).  We also need to
specify the `joinColumn` (SQLObject guesses the wrong name for it, like
everything else).

