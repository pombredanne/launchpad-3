# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""tales.py doctests."""

from doctest import DocTestSuite
import unittest

from zope.component import getAdapter
from zope.traversing.interfaces import IPathAdapter

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


def test_requestapi():
    """
    >>> from lp.app.browser.tales import IRequestAPI, RequestAPI
    >>> from lp.registry.interfaces.person import IPerson
    >>> from zope.interface.verify import verifyObject

    >>> class FakePrincipal:
    ...     def __conform__(self, protocol):
    ...         if protocol is IPerson:
    ...             return "This is a person"
    ...

    >>> class FakeApplicationRequest:
    ...    principal = FakePrincipal()
    ...    def getURL(self):
    ...        return 'http://launchpad.dev/'
    ...

    Let's make a fake request, where request.principal is a FakePrincipal
    object.  We can use a class or an instance here.  It really doesn't
    matter.

    >>> request = FakeApplicationRequest()
    >>> adapter = RequestAPI(request)

    >>> verifyObject(IRequestAPI, adapter)
    True

    >>> adapter.person
    'This is a person'

    """


def test_cookie_scope():
    """
    The 'request/lp:cookie_scope' TALES expression returns a string
    that represents the scope parameters necessary for a cookie to be
    available for the entire Launchpad site.  It takes into account
    the request URL and the cookie_domains setting in launchpad.conf.

        >>> from lp.app.browser.tales import RequestAPI
        >>> def cookie_scope(url):
        ...     class FakeRequest:
        ...         def getURL(self):
        ...             return url
        ...     return RequestAPI(FakeRequest()).cookie_scope

    The cookie scope will use the secure attribute if the request was
    secure:

        >>> print cookie_scope('http://launchpad.net/')
        ; Path=/; Domain=.launchpad.net
        >>> print cookie_scope('https://launchpad.net/')
        ; Path=/; Secure; Domain=.launchpad.net

    The domain parameter is omitted for domains that appear to be
    separate from a Launchpad instance, such as shipit:

        >>> print cookie_scope('https://shipit.ubuntu.com/')
        ; Path=/; Secure
    """


def test_dbschemaapi():
    """
    >>> from lp.app.browser.tales import DBSchemaAPI
    >>> from lp.code.enums import BranchType

    The syntax to get the title is: number/lp:DBSchemaClass

    >>> (str(DBSchemaAPI(1).traverse('BranchType', []))
    ...  == BranchType.HOSTED.title)
    True

    Using an inappropriate number should give a KeyError.

    >>> DBSchemaAPI(99).traverse('BranchType', [])
    Traceback (most recent call last):
    ...
    KeyError: 99

    Using a dbschema name that doesn't exist should give a LocationError

    >>> DBSchemaAPI(99).traverse('NotADBSchema', [])
    Traceback (most recent call last):
    ...
    LocationError: 'NotADBSchema'

    """


class TestPersonFormatterAPI(TestCaseWithFactory):
    """Tests for PersonFormatterAPI"""

    layer = DatabaseFunctionalLayer

    def test_nameLink(self):
        """The nameLink links to the URL with the person name as the text."""
        person = self.factory.makePerson()
        formatter = getAdapter(person, IPathAdapter, 'fmt')
        result = formatter.nameLink(None)
        expected = '<a href="%s" class="sprite person">%s</a>' % (
            formatter.url(), person.name)
        self.assertEqual(expected, result)


def test_suite():
    """Return this module's doctest Suite. Unit tests are also run."""
    suite = unittest.TestSuite()
    suite.addTests(DocTestSuite())
    suite.addTests(unittest.TestLoader().loadTestsFromName(__name__))
    return suite


if __name__ == '__main__':
    unittest.main()
