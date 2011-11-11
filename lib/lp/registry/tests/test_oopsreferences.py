# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests of the oopsreferences core."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )

from pytz import utc

from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.model.oopsreferences import referenced_oops
from lp.services.messages.model.message import (
    Message,
    MessageSet,
    )
from lp.testing import TestCaseWithFactory, person_logged_in


class TestOopsReferences(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestOopsReferences, self).setUp()
        self.store = IStore(Message)

    def test_oops_in_messagechunk(self):
        oopsid = "OOPS-abcdef1234"
        MessageSet().fromText('foo', "foo %s bar" % oopsid)
        self.store.flush()
        now = datetime.now(tz=utc)
        day = timedelta(days=1)
        self.failUnlessEqual(
            set([oopsid.upper()]),
            referenced_oops(now - day, now, "product=1", {}))
        self.failUnlessEqual(
            set(),
            referenced_oops(now + day, now + day, "product=1", {}))

    def test_oops_in_messagesubject(self):
        oopsid = "OOPS-abcdef1234"
        self.factory.makeEmailMessage()
        MessageSet().fromText("Crash with %s" % oopsid, "body")
        self.store.flush()
        now = datetime.now(tz=utc)
        day = timedelta(days=1)
        self.failUnlessEqual(
            set([oopsid.upper()]),
            referenced_oops(now - day, now, "product=1", {}))
        self.failUnlessEqual(
            set(),
            referenced_oops(now + day, now + day, "product=1", {}))

    def test_oops_in_bug_title(self):
        oopsid = "OOPS-abcdef1234"
        bug = self.factory.makeBug()
        with person_logged_in(bug.owner):
            bug.title = "Crash with %s" % oopsid
        self.store.flush()
        now = datetime.now(tz=utc)
        day = timedelta(days=1)
        self.failUnlessEqual(
            set([oopsid.upper()]),
            referenced_oops(now - day, now, "product=1", {}))
        self.failUnlessEqual(
            set(),
            referenced_oops(now + day, now + day, "product=1", {}))

    def test_oops_in_bug_description(self):
        oopsid = "OOPS-abcdef1234"
        bug = self.factory.makeBug()
        with person_logged_in(bug.owner):
            bug.description = "Crash with %s" % oopsid
        self.store.flush()
        now = datetime.now(tz=utc)
        day = timedelta(days=1)
        self.failUnlessEqual(
            set([oopsid.upper()]),
            referenced_oops(now - day, now, "product=1", {}))
        self.failUnlessEqual(
            set(),
            referenced_oops(now + day, now + day, "product=1", {}))

    def test_oops_in_question_title(self):
        oopsid = "OOPS-abcdef1234"
        question = self.factory.makeQuestion(title="Crash with %s" % oopsid)
        self.store.flush()
        now = datetime.now(tz=utc)
        day = timedelta(days=1)
        self.failUnlessEqual(
            set([oopsid.upper()]),
            referenced_oops(now - day, now, "product=%(product)s",
            {'product': question.product.id}))
        self.failUnlessEqual(
            set([]),
            referenced_oops(now + day, now + day, "product=%(product)s",
            {'product': question.product.id}))

    def test_oops_in_question_wrong_context(self):
        oopsid = "OOPS-abcdef1234"
        question = self.factory.makeQuestion(title="Crash with %s" % oopsid)
        self.store.flush()
        now = datetime.now(tz=utc)
        day = timedelta(days=1)
        self.store.flush()
        self.failUnlessEqual(
            set(),
            referenced_oops(now - day, now, "product=%(product)s",
            {'product': question.product.id + 1}))

    def test_oops_in_question_description(self):
        oopsid = "OOPS-abcdef1234"
        question = self.factory.makeQuestion(
            description="Crash with %s" % oopsid)
        self.store.flush()
        now = datetime.now(tz=utc)
        day = timedelta(days=1)
        self.failUnlessEqual(
            set([oopsid.upper()]),
            referenced_oops(now - day, now, "product=%(product)s",
            {'product': question.product.id}))
        self.failUnlessEqual(
            set([]),
            referenced_oops(now + day, now + day, "product=%(product)s",
            {'product': question.product.id}))

    def test_oops_in_question_whiteboard(self):
        oopsid = "OOPS-abcdef1234"
        question = self.factory.makeQuestion()
        with person_logged_in(question.owner):
            question.whiteboard = "Crash with %s" % oopsid
            self.store.flush()
        now = datetime.now(tz=utc)
        day = timedelta(days=1)
        self.failUnlessEqual(
            set([oopsid.upper()]),
            referenced_oops(now - day, now, "product=%(product)s",
            {'product': question.product.id}))
        self.failUnlessEqual(
            set([]),
            referenced_oops(now + day, now + day, "product=%(product)s",
            {'product': question.product.id}))

    def test_oops_in_question_distribution(self):
        oopsid = "OOPS-abcdef1234"
        distro = self.factory.makeDistribution()
        question = self.factory.makeQuestion(target=distro)
        with person_logged_in(question.owner):
            question.whiteboard = "Crash with %s" % oopsid
            self.store.flush()
        now = datetime.now(tz=utc)
        day = timedelta(days=1)
        self.failUnlessEqual(
            set([oopsid.upper()]),
            referenced_oops(now - day, now, "distribution=%(distribution)s",
            {'distribution': distro.id}))
        self.failUnlessEqual(
            set([]),
            referenced_oops(now + day, now + day,
            "distribution=%(distribution)s", {'distribution': distro.id}))

    def test_referenced_oops_in_urls_bug_663249(self):
        # Sometimes OOPS ids appears as part of an URL. These should could as
        # a reference even though they are not formatted specially - this
        # requires somewhat special handling in the reference calculation
        # function.
        oopsid = "OOPS-abcdef1234"
        bug = self.factory.makeBug()
        with person_logged_in(bug.owner):
            bug.description = (
                "foo https://lp-oops.canonical.com/oops.py?oopsid=%s bar"
                % oopsid)
            self.store.flush()
        now = datetime.now(tz=utc)
        day = timedelta(days=1)
        self.failUnlessEqual(
            set([oopsid.upper()]),
            referenced_oops(now - day, now, "product=1", {}))
        self.failUnlessEqual(
            set([]),
            referenced_oops(now + day, now + day, "product=1", {}))
