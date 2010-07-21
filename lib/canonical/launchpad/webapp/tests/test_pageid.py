# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test page ID generation."""

__metaclass__ = type


import unittest

from lp.testing import TestCase
from canonical.launchpad.webapp.servers import WebServicePublication


class FakeContext:
    """A context object that doesn't do anything."""


class FakeRequest:
    """A request that has just enough request-ness for page ID generation."""

    query_string_params = {}
    form_values = {}

    def get(self, key):
        return self.form_values.get(key)


class FakeView:
    """A view object that just has a fake context and request."""
    context = FakeContext()
    request = FakeRequest()


class TestAuthenticationOfPersonlessAccounts(TestCase):

    def test_pageid_without_op(self):
        # When the HTTP request does not have a named operation (ws.op) field
        # (either in the body or query string), the operation is included in
        # the page ID.
        publication = WebServicePublication(db=None)
        view = FakeView()
        context = FakeContext()
        pageid = publication.constructPageID(view, context)
        self.assertEqual(pageid, 'FakeContext:FakeView')

    def test_pageid_without_op_in_form(self):
        # When the HTTP request does not have a named operation (ws.op) field
        # (either in the body or query string), the operation is included in
        # the page ID.
        publication = WebServicePublication(db=None)
        view = FakeView()
        view.request.form_values['ws.op'] = 'operation-name'
        context = FakeContext()
        pageid = publication.constructPageID(view, context)
        self.assertEqual(pageid, 'FakeContext:operation-name')

    def test_pageid_without_op_in_query_string(self):
        # When the HTTP request does not have a named operation (ws.op) field
        # (either in the body or query string), the operation is included in
        # the page ID.
        publication = WebServicePublication(db=None)
        view = FakeView()
        view.request.query_string_params['ws.op'] = 'operation-name'
        context = FakeContext()
        pageid = publication.constructPageID(view, context)
        self.assertEqual(pageid, 'FakeContext:operation-name')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
