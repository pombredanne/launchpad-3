# Copyright 2004 Canonical Ltd.  All rights reserved.
#

import unittest
from zope.testing.doctestunit import DocTestSuite

def test_requestapi():
    """
    >>> from canonical.launchpad.webapp.tales import IRequestAPI, RequestAPI
    >>> from canonical.launchpad.interfaces import IPerson
    >>> from zope.interface.verify import verifyObject

    >>> class FakePrincipal:
    ...     def __conform__(self, protocol):
    ...         if protocol is IPerson:
    ...             return "This is a person"
    ...

    >>> class FakeApplicationRequest:
    ...    principal = FakePrincipal()
    ...

    Let's make a fake request, where request.principal is a FakePrincipal
    object.  We can use a class or an instance here.  It really doesn't
    matter.

    >>> request = FakeApplicationRequest
    >>> adapter = RequestAPI(request)

    >>> verifyObject(IRequestAPI, adapter)
    True

    >>> adapter.person
    'This is a person'

    """

def test_dbschemaapi():
    """
    >>> from canonical.launchpad.webapp.tales import DBSchemaAPI
    >>> from canonical.lp.dbschema import ManifestEntryType

    The syntax to get the title is: number/lp:DBSchemaClass

    >>> (str(DBSchemaAPI(4).traverse('ManifestEntryType', []))
    ...  == ManifestEntryType.TAR.title)
    True

    Using an inappropriate number should give a KeyError.

    >>> DBSchemaAPI(99).traverse('ManifestEntryType', [])
    Traceback (most recent call last):
    ...
    KeyError: 99

    Using a dbschema name that doesn't exist should give a TraversalError

    >>> DBSchemaAPI(99).traverse('NotADBSchema', [])
    Traceback (most recent call last):
    ...
    TraversalError: 'NotADBSchema'

    We should also test names that are in the dbschema module, but not in
    __all__.

    >>> import canonical.lp.dbschema
    >>> from canonical.lp.dbschema import Item
    >>> 'Item' not in canonical.lp.dbschema.__all__
    True
    >>> DBSchemaAPI(1).traverse('Item', [])
    Traceback (most recent call last):
    ...
    TraversalError: 'Item'

    """

def test_suite():
    suite = DocTestSuite()
    return suite


if __name__ == '__main__':
    unittest.main()
