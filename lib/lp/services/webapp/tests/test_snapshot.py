# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from lazr.lifecycle.interfaces import IObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from testtools.matchers import (
    Equals,
    MatchesAll,
    MatchesListwise,
    MatchesStructure,
    )
from zope.authentication.interfaces import IUnauthenticatedPrincipal
from zope.interface import (
    implementer,
    Interface,
    )
from zope.schema import Int

from lp.services.webapp.snapshot import notify_modified
from lp.testing import (
    EventRecorder,
    TestCaseWithFactory,
    )
from lp.testing.layers import ZopelessDatabaseLayer
from lp.testing.matchers import Provides


class IThing(Interface):

    attr = Int()


@implementer(IThing)
class Thing:

    def __init__(self, attr):
        self.attr = attr


class TestNotifyModified(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_generates_notification(self):
        obj = Thing(0)
        with EventRecorder() as recorder:
            with notify_modified(obj, ["attr"]):
                obj.attr = 1
        self.assertThat(recorder.events, MatchesListwise([
            MatchesAll(
                Provides(IObjectModifiedEvent),
                MatchesStructure(
                    object=MatchesStructure(attr=Equals(1)),
                    object_before_modification=MatchesAll(
                        Provides(IThing),
                        MatchesStructure(attr=Equals(0))),
                    edited_fields=Equals(["attr"]),
                    user=Provides(IUnauthenticatedPrincipal))),
            ]))

    def test_mutate_edited_fields_within_block(self):
        obj = Thing(0)
        with EventRecorder() as recorder:
            edited_fields = set()
            with notify_modified(obj, edited_fields):
                obj.attr = 1
                edited_fields.add("attr")
        self.assertThat(recorder.events, MatchesListwise([
            MatchesAll(
                Provides(IObjectModifiedEvent),
                MatchesStructure(
                    object=MatchesStructure(attr=Equals(1)),
                    object_before_modification=MatchesAll(
                        Provides(IThing),
                        MatchesStructure(attr=Equals(0))),
                    edited_fields=Equals(["attr"]),
                    user=Provides(IUnauthenticatedPrincipal))),
            ]))

    def test_yields_previous_object(self):
        obj = Thing(0)
        with notify_modified(obj, []) as previous_obj:
            obj.attr = 1
            self.assertIsInstance(previous_obj, Snapshot)
            self.assertEqual(0, previous_obj.attr)

    def test_different_user(self):
        obj = Thing(0)
        user = self.factory.makePerson()
        with EventRecorder() as recorder:
            with notify_modified(obj, ["attr"], user=user):
                obj.attr = 1
        self.assertThat(recorder.events, MatchesListwise([
            MatchesAll(
                Provides(IObjectModifiedEvent),
                MatchesStructure(
                    object=MatchesStructure(attr=Equals(1)),
                    object_before_modification=MatchesAll(
                        Provides(IThing),
                        MatchesStructure(attr=Equals(0))),
                    edited_fields=Equals(["attr"]),
                    user=Equals(user))),
            ]))
