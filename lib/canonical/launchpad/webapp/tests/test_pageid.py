# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test page ID generation."""

__metaclass__ = type


import unittest

from canonical.launchpad.webapp.servers import WebServicePublication
from lp.testing import TestCase


class FakeContext:
    """A context object that doesn't do anything."""


class FakeRequest:
    """A request that has just enough request-ness for page ID generation."""

    def __init__(self):
        self.query_string_params = {}
        self.form_values = {}

    def get(self, key):
        return self.form_values.get(key)


class FakeView:
    """A view object that just has a fake context and request."""

    def __init__(self):
        self.context = FakeContext()
        self.request = FakeRequest()


class TestWebServicePageIDs(TestCase):
    """Ensure that the web service enhances the page ID correctly."""

    def setUp(self):
        super(TestWebServicePageIDs, self).setUp()
        self.publication = WebServicePublication(db=None)
        self.view = FakeView()
        self.context = FakeContext()

    def makePageID(self):
        return self.publication.constructPageID(self.view, self.context)

    def test_pageid_without_op(self):
        # When the HTTP request does not have a named operation (ws.op) field
        # (either in the body or query string), the operation is included in
        # the page ID.
        self.assertEqual(
            self.makePageID(), 'FakeContext:FakeView')

    def test_pageid_without_op_in_form(self):
        # When the HTTP request does not have a named operation (ws.op) field
        # (either in the body or query string), the operation is included in
        # the page ID.
        self.view.request.form_values['ws.op'] = 'operation-name-1'
        self.assertEqual(
            self.makePageID(), 'FakeContext:FakeView:operation-name-1')

    def test_pageid_without_op_in_query_string(self):
        # When the HTTP request does not have a named operation (ws.op) field
        # (either in the body or query string), the operation is included in
        # the page ID.
        self.view.request.query_string_params['ws.op'] = 'operation-name-2'
        self.assertEqual(
            self.makePageID(), 'FakeContext:FakeView:operation-name-2')
