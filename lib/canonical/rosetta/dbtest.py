# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 15208f9c-d842-4424-9726-df34c4b406c0
"""Test of the SQL backend for Rosetta.

"""

__metaclass__ = type

# Zope imports
from zope.interface import implements, Interface, Attribute

# sqlos and SQLObject imports
from sqlos import SQLOS
from sqlobject import StringCol


"""
DROP TABLE RosettaTest;
CREATE TABLE RosettaTest (
    rosettatest SERIAL PRIMARY KEY,
    testname text,
    description text
    );
INSERT INTO RosettaTest (testname, description) VALUES
    ('t1', 'this is the t1 test object');

INSERT INTO RosettaTest (testname, description) VALUES
    ('t2', 'this is the t2 test object');

INSERT INTO RosettaTest (testname, description) VALUES
    ('foo bar baz', 'this is the foo bar baz test object');
"""

class ITest(Interface):
    """Testing database integration.  Contents.

    This interface will be going away soon.
    """

    name = Attribute("name")

    description = Attribute("description")

class ITests(Interface):
    """Testing database integration.  Container.

    This interface will be going away soon.
    """

    def __getitem__(name):
        """Returns the test object with the given name."""

    def __iter__():
        """Iterate over the available test objects."""


class Test(SQLOS):
    implements(ITest)

    _table = 'RosettaTest'
    _idName = 'rosettatest'
    _columns = [
        StringCol('name', dbName='testname'),
        StringCol('description', dbName='description'),
    ]

class Tests:
    implements(ITests)

    def __getitem__(self, name):
        """See ITests."""
        try:
            return Test.select(Test.q.name==name)[0]
        except IndexError:
            raise KeyError, name

    def __iter__(self):
        for obj in Test.select():
            yield obj

