# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from zope.component import getUtility

from lp.services.xref.interfaces import IXRefSet
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestXRefSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_create_and_find(self):
        creator = self.factory.makePerson()
        getUtility(IXRefSet).createByIDs(
            {('bar', 'foo'): {'creator': creator, 'metadata': {'test': 1234}},
             ('foo', 'baz'): {'creator': creator, 'metadata': {'test': 2468}}})

        self.assertEqual(
            {('bar', 'foo'): {'creator': creator, 'metadata': {'test': 1234}}},
            getUtility(IXRefSet).findByIDs(['bar']))
        self.assertEqual(
            {('bar', 'foo'): {'creator': creator, 'metadata': {'test': 1234}},
             ('baz', 'foo'): {'creator': creator, 'metadata': {'test': 2468}}},
            getUtility(IXRefSet).findByIDs(['foo']))
        self.assertEqual(
            {('baz', 'foo'): {'creator': creator, 'metadata': {'test': 2468}}},
            getUtility(IXRefSet).findByIDs(['baz']))
        self.assertEqual(
            getUtility(IXRefSet).findByIDs(['foo']),
            getUtility(IXRefSet).findByIDs(['bar', 'baz']))

    def test_deleteByIDs(self):
        getUtility(IXRefSet).createByIDs(
            {('bar', 'foo'): {}, ('foo', 'baz'): {}})
        self.assertEqual(['bar', 'baz'], getUtility(IXRefSet).findIDs('foo'))
        getUtility(IXRefSet).deleteByIDs([['foo', 'bar']])
        self.assertEqual(['baz'], getUtility(IXRefSet).findIDs('foo'))
