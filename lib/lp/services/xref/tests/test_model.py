# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from testtools.matchers import Equals
from zope.component import getUtility

from lp.services.xref.interfaces import IXRefSet
from lp.testing import (
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount


class TestXRefSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_findFrom(self):
        creator = self.factory.makePerson()
        getUtility(IXRefSet).create({
            ('a', 'bar'): {
                ('b', 'foo'): {'creator': creator, 'metadata': {'test': 1}}},
            ('b', 'foo'): {
                ('a', 'baz'): {'creator': creator, 'metadata': {'test': 2}}},
            })

        with StormStatementRecorder() as recorder:
            bar_refs = getUtility(IXRefSet).findFrom(('a', 'bar'))
        self.assertThat(recorder, HasQueryCount(Equals(2)))
        self.assertEqual(
            {('b', 'foo'): {'creator': creator, 'metadata': {'test': 1}}},
            bar_refs)

        with StormStatementRecorder() as recorder:
            foo_refs = getUtility(IXRefSet).findFrom(('b', 'foo'))
        self.assertThat(recorder, HasQueryCount(Equals(2)))
        self.assertEqual(
            {('a', 'bar'): {'creator': creator, 'metadata': {'test': 1}},
             ('a', 'baz'): {'creator': creator, 'metadata': {'test': 2}}},
            foo_refs)

        with StormStatementRecorder() as recorder:
            bar_refs = getUtility(IXRefSet).findFrom(('a', 'baz'))
        self.assertThat(recorder, HasQueryCount(Equals(2)))
        self.assertEqual(
            {('b', 'foo'): {'creator': creator, 'metadata': {'test': 2}}},
            bar_refs)

        with StormStatementRecorder() as recorder:
            bar_baz_refs = getUtility(IXRefSet).findFromMultiple(
                [('a', 'bar'), ('a', 'baz')])
        self.assertThat(recorder, HasQueryCount(Equals(2)))
        self.assertEqual(
            {('a', 'bar'): {
                ('b', 'foo'): {'creator': creator, 'metadata': {'test': 1}}},
             ('a', 'baz'): {
                ('b', 'foo'): {'creator': creator, 'metadata': {'test': 2}}}},
             bar_baz_refs)

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
