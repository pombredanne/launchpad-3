# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the bugcomment module."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
from itertools import count

from pytz import utc

from lp.bugs.browser.bugcomment import group_comments_with_activity
from lp.testing import TestCase


class BugActivityStub:

    def __init__(self, datechanged, person=None):
        self.datechanged = datechanged
        if person is None:
            person = PersonStub()
        self.person = person

    def __repr__(self):
        return "BugActivityStub(%r, %r)" % (
            self.datechanged.strftime('%Y-%m-%d--%H%M'), self.person)


class BugCommentStub:

    def __init__(self, datecreated, owner=None):
        self.datecreated = datecreated
        if owner is None:
            owner = PersonStub()
        self.owner = owner
        self.activity = []

    def __repr__(self):
        return "BugCommentStub(%r, %r)" % (
            self.datecreated.strftime('%Y-%m-%d--%H%M'), self.owner)


class PersonStub:

    ids = count(1)

    def __init__(self):
        self.id = next(self.ids)

    def __repr__(self):
        return "PersonStub#%d" % self.id


class TestGroupCommentsWithActivities(TestCase):
    """Tests for `group_comments_with_activities`."""

    def setUp(self):
        super(TestGroupCommentsWithActivities, self).setUp()
        self.now = datetime.now(utc)
        self.timestamps = (
            self.now + timedelta(minutes=counter)
            for counter in count(1))

    def group(self, comments, activities):
        return list(
            group_comments_with_activity(
                comments=comments, activities=activities))

    def test_empty(self):
        # Given no comments or activities the result is also empty.
        self.assertEqual(
            [], self.group(comments=[], activities=[]))

    def test_activity_empty_no_common_actor(self):
        # When no activities are passed in, and the comments passed in don't
        # have any common actors, no grouping is possible.
        comments = [
            BugCommentStub(next(self.timestamps))
            for number in xrange(5)]
        self.assertEqual(
            comments, self.group(comments=comments, activities=[]))

    def test_comments_empty_no_common_actor(self):
        # When no comments are passed in, and the activities passed in don't
        # have any common actors, no grouping is possible.
        activities = [
            BugActivityStub(next(self.timestamps))
            for number in xrange(5)]
        self.assertEqual(
            [[activity] for activity in activities], self.group(
                comments=[], activities=activities))

    def test_no_common_actor(self):
        # When each activities and comment given has a different actor then no
        # grouping is possible.
        activity1 = BugActivityStub(next(self.timestamps))
        comment1 = BugCommentStub(next(self.timestamps))
        activity2 = BugActivityStub(next(self.timestamps))
        comment2 = BugCommentStub(next(self.timestamps))

        activities = set([activity1, activity2])
        comments = set([comment1, comment2])

        self.assertEqual(
            [[activity1], comment1, [activity2], comment2],
            self.group(comments=comments, activities=activities))

    def test_comment_then_activity_close_by_common_actor(self):
        # An activity shortly after a comment by the same person is grouped
        # into the comment.
        actor = PersonStub()
        comment = BugCommentStub(next(self.timestamps), actor)
        activity = BugActivityStub(next(self.timestamps), actor)
        grouped = self.group(comments=[comment], activities=[activity])
        self.assertEqual([comment], grouped)
        self.assertEqual([activity], comment.activity)

    def test_activity_then_comment_close_by_common_actor(self):
        # An activity shortly before a comment by the same person is grouped
        # into the comment.
        actor = PersonStub()
        activity = BugActivityStub(next(self.timestamps), actor)
        comment = BugCommentStub(next(self.timestamps), actor)
        grouped = self.group(comments=[comment], activities=[activity])
        self.assertEqual([comment], grouped)
        self.assertEqual([activity], comment.activity)

    def test_interleaved_activity_with_comments_by_common_actor(self):
        # Activities shortly before and after a comment are grouped into the
        # comment's activity.
        actor = PersonStub()
        activity1 = BugActivityStub(next(self.timestamps), actor)
        comment = BugCommentStub(next(self.timestamps), actor)
        activity2 = BugActivityStub(next(self.timestamps), actor)
        grouped = self.group(
            comments=[comment], activities=[activity1, activity2])
        self.assertEqual([comment], grouped)
        self.assertEqual([activity1, activity2], comment.activity)

    def test_common_actor_over_a_prolonged_time(self):
        # There is a timeframe for grouping events. Anything outside of that
        # window is considered separate.
        actor = PersonStub()
        activities = [
            BugActivityStub(next(self.timestamps), actor)
            for count in xrange(8)]
        grouped = self.group(comments=[], activities=activities)
        self.assertEqual(2, len(grouped))
        self.assertEqual(activities[:5], grouped[0])
        self.assertEqual(activities[5:], grouped[1])

    def test_two_comments_by_common_actor(self):
        # Only one comment will ever appear in a group.
        actor = PersonStub()
        comment1 = BugCommentStub(next(self.timestamps), actor)
        comment2 = BugCommentStub(next(self.timestamps), actor)
        grouped = self.group(comments=[comment1, comment2], activities=[])
        self.assertEqual([comment1, comment2], grouped)

    def test_two_comments_with_activity_by_common_actor(self):
        # Activity gets associated with earlier comment when all other factors
        # are unchanging.
        actor = PersonStub()
        activity1 = BugActivityStub(next(self.timestamps), actor)
        comment1 = BugCommentStub(next(self.timestamps), actor)
        activity2 = BugActivityStub(next(self.timestamps), actor)
        comment2 = BugCommentStub(next(self.timestamps), actor)
        activity3 = BugActivityStub(next(self.timestamps), actor)
        grouped = self.group(
            comments=[comment1, comment2],
            activities=[activity1, activity2, activity3])
        self.assertEqual([comment1, comment2], grouped)
        self.assertEqual([activity1, activity2], comment1.activity)
        self.assertEqual([activity3], comment2.activity)
