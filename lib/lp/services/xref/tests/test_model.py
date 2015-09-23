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

    def test_findByIDs(self):
        creator = self.factory.makePerson()
        getUtility(IXRefSet).createByIDs(
            {('bar', 'foo'): {'creator': creator, 'metadata': {'test': 1234}},
             ('foo', 'baz'): {'creator': creator, 'metadata': {'test': 2468}}})

        with StormStatementRecorder() as recorder:
            bar_refs = getUtility(IXRefSet).findByIDs(['bar'])
        self.assertThat(recorder, HasQueryCount(Equals(2)))
        self.assertEqual(
            {('bar', 'foo'): {'creator': creator, 'metadata': {'test': 1234}}},
            bar_refs)

        with StormStatementRecorder() as recorder:
            foo_refs = getUtility(IXRefSet).findByIDs(['foo'])
        self.assertThat(recorder, HasQueryCount(Equals(2)))
        self.assertEqual(
            {('foo', 'bar'): {'creator': creator, 'metadata': {'test': 1234}},
             ('foo', 'baz'): {'creator': creator, 'metadata': {'test': 2468}}},
            foo_refs)

        with StormStatementRecorder() as recorder:
            bar_refs = getUtility(IXRefSet).findByIDs(['baz'])
        self.assertThat(recorder, HasQueryCount(Equals(2)))
        self.assertEqual(
            {('baz', 'foo'): {'creator': creator, 'metadata': {'test': 2468}}},
            bar_refs)

        with StormStatementRecorder() as recorder:
            bar_baz_refs = getUtility(IXRefSet).findByIDs(['bar', 'baz'])
        self.assertThat(recorder, HasQueryCount(Equals(2)))
        self.assertEqual(
            {(k[1], k[0]): v for k, v in foo_refs.items()}, bar_baz_refs)

    def test_deleteByIDs(self):
        getUtility(IXRefSet).createByIDs(
            {('bar', 'foo'): {}, ('foo', 'baz'): {}})
        self.assertEqual(['bar', 'baz'], getUtility(IXRefSet).findIDs('foo'))
        with StormStatementRecorder() as recorder:
            getUtility(IXRefSet).deleteByIDs([['foo', 'bar']])
        self.assertThat(recorder, HasQueryCount(Equals(1)))
        self.assertEqual(['baz'], getUtility(IXRefSet).findIDs('foo'))
