# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test page ID generation."""

__metaclass__ = type


from zope.interface import implements
from lazr.restful.interfaces import ICollectionResource

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


class FakeCollectionResourceView(FakeView):
    """A view object that provides ICollectionResource."""
    implements(ICollectionResource)

    def __init__(self):
        super(FakeCollectionResourceView, self).__init__()
        self.type_url = (
            u'https://launchpad.dev/api/devel/#milestone-page-resource')


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


class TestCollectionResourcePageIDs(TestCase):
    """Ensure page ids for collections display the origin page resource."""

    def setUp(self):
        super(TestCollectionResourcePageIDs, self).setUp()
        self.publication = WebServicePublication(db=None)
        self.view = FakeCollectionResourceView()
        self.context = FakeContext()

    def makePageID(self):
        return self.publication.constructPageID(self.view, self.context)

    def test_origin_pageid_for_collection(self):
        # When the view provides a ICollectionResource, make sure the origin
        # page resource is included in the page ID.
        self.assertEqual(
            self.makePageID(),
            'FakeContext:FakeCollectionResourceView:#milestone-page-resource')


class TestPageIdCorners(TestCase):
    """Ensure that the page ID generation handles corner cases well."""

    def setUp(self):
        super(TestPageIdCorners, self).setUp()
        self.publication = WebServicePublication(db=None)
        self.view = FakeView()
        self.context = FakeContext()

    def makePageID(self):
        return self.publication.constructPageID(self.view, self.context)

    def test_pageid_with_multiple_op_fields(self):
        # The publisher will combine mutliple form values with the same name
        # into a list.  If those values are for "ws.op", the page ID mechanism
        # should just ignore the op alltogether.  (It used to generate an
        # error, see bug 810113).
        self.view.request.form_values['ws.op'] = ['one', 'another']
        self.assertEqual(self.makePageID(), 'FakeContext:FakeView')
