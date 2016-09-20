# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import datetime

import pytz
from testtools.matchers import (
    ContainsDict,
    Equals,
    MatchesDict,
    )
from zope.component import getUtility

from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import flush_database_caches
from lp.services.xref.interfaces import IXRefSet
from lp.services.xref.model import XRef
from lp.testing import (
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount


class TestXRefSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_create_sets_date_created(self):
        # date_created defaults to now, but can be overridden.
        old = datetime.datetime.strptime('2005-01-01', '%Y-%m-%d').replace(
            tzinfo=pytz.UTC)
        now = IStore(XRef).execute(
            "SELECT CURRENT_TIMESTAMP AT TIME ZONE 'UTC'"
            ).get_one()[0].replace(tzinfo=pytz.UTC)
        getUtility(IXRefSet).create({
            ('a', '1'): {('b', 'foo'): {}},
            ('a', '2'): {('b', 'bar'): {'date_created': old}}})
        rows = IStore(XRef).find(
            (XRef.from_id, XRef.to_id, XRef.date_created),
            XRef.from_type == 'a')
        self.assertContentEqual(
            [('1', 'foo', now), ('2', 'bar', old)], rows)

    def test_create_sets_int_columns(self):
        # The string ID columns have integers equivalents for quick and
        # easy joins to integer PKs. They're set automatically when the
        # string ID looks like an integer.
        getUtility(IXRefSet).create({
            ('a', '1234'): {('b', 'foo'): {}, ('b', '2468'): {}},
            ('a', '12ab'): {('b', '1234'): {}, ('b', 'foo'): {}}})
        rows = IStore(XRef).find(
            (XRef.from_type, XRef.from_id, XRef.from_id_int, XRef.to_type,
             XRef.to_id, XRef.to_id_int),
            XRef.from_type == 'a')
        self.assertContentEqual(
            [('a', '1234', 1234, 'b', 'foo', None),
             ('a', '1234', 1234, 'b', '2468', 2468),
             ('a', '12ab', None, 'b', '1234', 1234),
             ('a', '12ab', None, 'b', 'foo', None)
             ],
            rows)

    def test_findFrom(self):
        creator = self.factory.makePerson()
        now = IStore(XRef).execute(
            "SELECT CURRENT_TIMESTAMP AT TIME ZONE 'UTC'"
            ).get_one()[0].replace(tzinfo=pytz.UTC)
        getUtility(IXRefSet).create({
            ('a', 'bar'): {
                ('b', 'foo'): {'creator': creator, 'metadata': {'test': 1}}},
            ('b', 'foo'): {
                ('a', 'baz'): {'creator': creator, 'metadata': {'test': 2}}},
            ('b', 'baz'): {
                ('a', 'quux'): {'creator': creator, 'metadata': {'test': 3}}},
            })

        with StormStatementRecorder() as recorder:
            bar_refs = getUtility(IXRefSet).findFrom(('a', 'bar'))
        self.assertThat(recorder, HasQueryCount(Equals(2)))
        self.assertEqual(
            {('b', 'foo'): {
                'creator': creator, 'date_created': now,
                'metadata': {'test': 1}}},
            bar_refs)

        with StormStatementRecorder() as recorder:
            foo_refs = getUtility(IXRefSet).findFrom(('b', 'foo'))
        self.assertThat(recorder, HasQueryCount(Equals(2)))
        self.assertEqual(
            {('a', 'bar'): {
                'creator': creator, 'date_created': now,
                'metadata': {'test': 1}},
             ('a', 'baz'): {
                 'creator': creator, 'date_created': now,
                 'metadata': {'test': 2}}},
            foo_refs)

        with StormStatementRecorder() as recorder:
            bar_refs = getUtility(IXRefSet).findFrom(('a', 'baz'))
        self.assertThat(recorder, HasQueryCount(Equals(2)))
        self.assertEqual(
            {('b', 'foo'): {
                'creator': creator, 'date_created': now,
                'metadata': {'test': 2}}},
            bar_refs)

        with StormStatementRecorder() as recorder:
            bar_baz_refs = getUtility(IXRefSet).findFromMany(
                [('a', 'bar'), ('a', 'baz')])
        self.assertThat(recorder, HasQueryCount(Equals(2)))
        self.assertEqual(
            {('a', 'bar'): {
                ('b', 'foo'): {
                    'creator': creator, 'date_created': now,
                    'metadata': {'test': 1}}},
             ('a', 'baz'): {
                ('b', 'foo'): {
                    'creator': creator, 'date_created': now,
                    'metadata': {'test': 2}}}},
             bar_baz_refs)

        with StormStatementRecorder() as recorder:
            bar_foo_refs = getUtility(IXRefSet).findFromMany(
                [('a', 'bar'), ('a', 'nonexistent'), ('b', 'baz')])
        self.assertThat(recorder, HasQueryCount(Equals(2)))
        self.assertEqual(
            {('a', 'bar'): {
                ('b', 'foo'): {
                    'creator': creator, 'date_created': now,
                    'metadata': {'test': 1}}},
             ('b', 'baz'): {
                ('a', 'quux'): {
                    'creator': creator, 'date_created': now,
                    'metadata': {'test': 3}}}},
             bar_foo_refs)

    def test_findFrom_creator(self):
        # findFrom issues a single query to get all of the people.
        people = [self.factory.makePerson() for i in range(3)]
        getUtility(IXRefSet).create({
            ('a', '0'): {
                ('b', '0'): {'creator': people[2]},
                ('b', '1'): {'creator': people[0]},
                ('b', '2'): {'creator': people[1]},
                },
            })
        flush_database_caches()
        with StormStatementRecorder() as recorder:
            xrefs = getUtility(IXRefSet).findFrom(('a', '0'))
        self.assertThat(
            xrefs,
            MatchesDict({
                ('b', '0'): ContainsDict({'creator': Equals(people[2])}),
                ('b', '1'): ContainsDict({'creator': Equals(people[0])}),
                ('b', '2'): ContainsDict({'creator': Equals(people[1])}),
                }))
        self.assertThat(recorder, HasQueryCount(Equals(2)))

    def test_findFrom_types(self):
        # findFrom can look for only particular types of related
        # objects.
        getUtility(IXRefSet).create({
            ('a', '1'): {('a', '2'): {}, ('b', '3'): {}},
            ('b', '4'): {('a', '5'): {}, ('c', '6'): {}},
            })
        self.assertContentEqual(
            [('a', '2')],
            getUtility(IXRefSet).findFrom(('a', '1'), types=['a', 'c']).keys())
        self.assertContentEqual(
            [('a', '5'), ('c', '6')],
            getUtility(IXRefSet).findFrom(('b', '4'), types=['a', 'c']).keys())

        # Asking for no types or types that don't exist finds nothing.
        self.assertContentEqual(
            [],
            getUtility(IXRefSet).findFrom(('b', '4'), types=[]).keys())
        self.assertContentEqual(
            [],
            getUtility(IXRefSet).findFrom(('b', '4'), types=['d']).keys())

    def test_findFromMany_none(self):
        self.assertEqual({}, getUtility(IXRefSet).findFromMany([]))

    def test_delete(self):
        getUtility(IXRefSet).create({
            ('a', 'bar'): {('b', 'foo'): {}},
            ('b', 'foo'): {('a', 'baz'): {}},
            })
        self.assertContentEqual(
            [('a', 'bar'), ('a', 'baz')],
            getUtility(IXRefSet).findFrom(('b', 'foo')).keys())
        with StormStatementRecorder() as recorder:
            getUtility(IXRefSet).delete({('b', 'foo'): [('a', 'bar')]})
        self.assertThat(recorder, HasQueryCount(Equals(1)))
        self.assertEqual(
            [('a', 'baz')],
            getUtility(IXRefSet).findFrom(('b', 'foo')).keys())
