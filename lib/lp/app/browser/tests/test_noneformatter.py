# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.registry.browser.tales.NoneFormatter"""

__metaclass__ = type


from zope.component import queryAdapter
from zope.traversing.interfaces import (
    IPathAdapter,
    TraversalError,
    )

from canonical.testing.layers import FunctionalLayer
from lp.testing import TestCaseWithFactory


class TestXHTMLRepresentations(TestCaseWithFactory):

    layer = FunctionalLayer

    def test_valid_traversal(self):
        adapter = queryAdapter(None, IPathAdapter, 'fmt')
        traverse = getattr(adapter, 'traverse', None)

        allowed_names = set([
            'approximatedate',
            'approximateduration',
            'break-long-words',
            'date',
            'datetime',
            'displaydate',
            'isodate',
            'email-to-html',
            'exactduration',
            'lower',
            'nice_pre',
            'nl_to_br',
            'pagetitle',
            'rfc822utcdatetime',
            'text-to-html',
            'time',
            'url',
            ])

        for name in allowed_names:
            self.assertEqual('', traverse(name, []))

    def test_invalid_traversal(self):
        adapter = queryAdapter(None, IPathAdapter, 'fmt')
        traverse = getattr(adapter, 'traverse', None)
        self.failUnlessRaises(TraversalError, traverse, "foo", [])

    def test_link(self):
        adapter = queryAdapter(None, IPathAdapter, 'fmt')
        traverse = getattr(adapter, 'traverse', None)
        self.assertEqual('None', traverse('link', []))

    def test_shorten_traversal(self):
        adapter = queryAdapter(None, IPathAdapter, 'fmt')
        traverse = getattr(adapter, 'traverse', None)
        extra = ['1', '2']
        self.assertEqual('', traverse('shorten', extra))
        self.assertEqual(['1'],extra)
