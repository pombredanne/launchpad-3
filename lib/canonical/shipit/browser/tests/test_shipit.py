# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Unit tests for Shipit views."""

__metaclass__ = type

import unittest

from canonical.shipit.browser.shipit import (
    ShipitOpenIDCallbackForServerCDsView, ShipitOpenIDCallbackView,
    ShipitOpenIDLoginForServerCDsView, ShipitOpenIDLoginView)
from canonical.shipit.model.shipit import ShipItSurvey
from canonical.launchpad.layers import setFirstLayer
from canonical.shipit.layers import ShipItUbuntuLayer
from canonical.shipit.systemhome import ShipItApplication
from lp.testing import login_person, TestCaseWithFactory
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import DatabaseFunctionalLayer


class TestShipitLoginViewsWithUserAlreadyLoggedIn(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.application = ShipItApplication()
        self.person = self.factory.makePerson()
        self.request = LaunchpadTestRequest()
        setFirstLayer(self.request, ShipItUbuntuLayer)
        login_person(self.person, self.request)

    def _createView(self, klass):
        view = klass(self.application, self.request)
        view.initialize()
        return view

    def test_ShipitOpenIDLoginView_redirects(self):
        view = self._createView(ShipitOpenIDLoginView)
        self.failUnless(view._isRedirected())
        self.failUnlessEqual(
            view.request.response.getHeader('Location'), '/myrequest')

    def test_ShipitOpenIDCallbackView_redirects(self):
        view = self._createView(ShipitOpenIDCallbackView)
        self.failUnless(view._isRedirected())
        self.failUnlessEqual(
            view.request.response.getHeader('Location'), '/myrequest')

    def test_ShipitOpenIDLoginForServerCDsView_redirects(self):
        # When the user hasn't answered the survey, he's taken to the /survey
        # page.
        view = self._createView(ShipitOpenIDLoginForServerCDsView)
        self.failUnless(view._isRedirected())
        self.failUnlessEqual(
            view.request.response.getHeader('Location'), '/survey')

        # After answering the survey, though, the user would be taken to
        # /myrequest-server.
        survey = ShipItSurvey(account=self.person.account)
        view = self._createView(ShipitOpenIDLoginForServerCDsView)
        self.failUnless(view._isRedirected())
        self.failUnlessEqual(
            view.request.response.getHeader('Location'), '/myrequest-server')

    def test_ShipitOpenIDCallbackForServerCDsView_redirects(self):
        # When the user hasn't answered the survey, he's taken to the /survey
        # page.
        view = self._createView(ShipitOpenIDCallbackForServerCDsView)
        self.failUnless(view._isRedirected())
        self.failUnlessEqual(
            view.request.response.getHeader('Location'), '/survey')

        # After answering the survey, though, the user would be taken to
        # /myrequest-server.
        survey = ShipItSurvey(account=self.person.account)
        view = self._createView(ShipitOpenIDCallbackForServerCDsView)
        self.failUnless(view._isRedirected())
        self.failUnlessEqual(
            view.request.response.getHeader('Location'), '/myrequest-server')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
