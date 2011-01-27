# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import login
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.soyuz.browser.builder import BuilderEditView
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod
from lp.testing.sampledata import ADMIN_EMAIL


class TestBuilderEditView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBuilderEditView, self).setUp()
        # Login as an admin to ensure access to the view's context
        # object.
        login(ADMIN_EMAIL)
        self.builder = removeSecurityProxy(self.factory.makeBuilder())

    def initialize_view(self):
        form = {
            "field.manual" : "on",
            "field.actions.update" : "Change",
            }
        request = LaunchpadTestRequest(method="POST", form=form)
        view = BuilderEditView(self.builder, request)
        return view

    def test_posting_form_doesnt_call_slave_xmlrpc(self):
        # Posting the +edit for should not call isAvailable, which
        # would do xmlrpc to a slave builder and is explicitly forbidden
        # in a webapp process.
        view = self.initialize_view()

        # Stub out the slaveStatusSentence() method with a fake one that
        # records if it's been called.
        view.context.slaveStatusSentence = FakeMethod(result=[0])

        view.initialize()

        # If the dummy slaveStatusSentence() was called the call count
        # would not be zero.
        self.assertTrue(view.context.slaveStatusSentence.call_count == 0 )
