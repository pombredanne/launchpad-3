# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from storm.locals import Store
from testtools.matchers import Equals
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import login
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.soyuz.browser.builder import BuilderEditView
from lp.testing import (
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod
from lp.testing.matchers import HasQueryCount
from lp.testing.sampledata import ADMIN_EMAIL
from lp.testing.views import create_initialized_view


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
            "field.manual": "on",
            "field.actions.update": "Change",
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
        self.assertTrue(view.context.slaveStatusSentence.call_count == 0)


class TestBuilderHistoryView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def createRecipeBuildWithBuilder(self, builder=None):
        build = self.factory.makeSourcePackageRecipeBuild()
        Store.of(build).flush()
        if builder is None:
            builder = self.factory.makeBuilder()
        removeSecurityProxy(build).builder = builder
        return build

    def test_build_history_queries_count(self):
        # The number of queries issued by setupBuildList is not dependent
        # on the number of builds.
        builder = self.factory.makeBuilder()
        [self.createRecipeBuildWithBuilder(builder) for i in xrange(2)]
        # Record how many queries are issued when setupBuildList is
        # called with 2 builds.
        with StormStatementRecorder() as recorder1:
            view = create_initialized_view(builder, '+history')
            view.setupBuildList()
            self.assertEqual(2, len(view.complete_builds))
        # Create two more builds.
        [self.createRecipeBuildWithBuilder(builder) for i in xrange(2)]
        # Record again the number of queries issued.
        with StormStatementRecorder() as recorder2:
            view = create_initialized_view(builder, '+history')
            view.setupBuildList()
            self.assertEqual(4, len(view.complete_builds))

        self.assertThat(recorder2, HasQueryCount(Equals(recorder1.count)))
