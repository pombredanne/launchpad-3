# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from zope.testing.doctest import DocTestSuite
from zope.interface import implements
from zope.session.interfaces import ISession, ISessionData
from zope.app.testing import ztapi, placelesssetup
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.interfaces.http import IHTTPApplicationResponse
from zope.publisher.browser import TestRequest

from canonical.launchpad.webapp.interfaces import (
        INotificationRequest, INotificationResponse
        )
from canonical.launchpad.webapp.notifications import NotificationResponse
from canonical.launchpad.webapp.menu import structured

class MockSession(dict):
    implements(ISession)

    def __getitem__(self, key):
        try:
            return super(MockSession, self).__getitem__(key)
        except KeyError:
            self[key] = MockSessionData()
            return super(MockSession, self).__getitem__(key)


class MockSessionData(dict):
    implements(ISessionData)

    lastAccessTime = 0

    def __call__(self, whatever):
        return self


class MockHTTPApplicationResponse:
    implements(IHTTPApplicationResponse)

    def redirect(self, location, status=None):
        """Just report the redirection to the doctest"""
        if status is None:
            status=302
        print '%d: %s' % (status, location)


def adaptNotificationRequestToResponse(request):
    try:
        return request.response
    except AttributeError:
        response = NotificationResponse()
        request.response = response
        response._request = request
        return response


def setUp(test):
    placelesssetup.setUp()
    mock_session = MockSession()
    ztapi.provideAdapter(
            INotificationRequest, ISession, lambda x: mock_session
            )
    ztapi.provideAdapter(
            INotificationResponse, ISession, lambda x: mock_session
            )
    ztapi.provideAdapter(
            INotificationRequest, INotificationResponse,
            adaptNotificationRequestToResponse
            )

    mock_browser_request = TestRequest()
    ztapi.provideAdapter(
            INotificationRequest, IBrowserRequest,
            lambda x: mock_browser_request
            )

    test.globs['MockResponse'] = MockHTTPApplicationResponse
    test.globs['structured'] = structured


def tearDown(test):
    placelesssetup.tearDown()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(
        'canonical.launchpad.webapp.notifications',
        setUp=setUp, tearDown=tearDown,
        ))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

