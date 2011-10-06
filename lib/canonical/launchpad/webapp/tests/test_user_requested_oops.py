# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for the user requested oops using ++oops++ traversal."""

__metaclass__ = type


from lazr.restful.utils import get_current_browser_request
from zope.component import getUtility
from zope.error.interfaces import IErrorReportingUtility

from canonical.launchpad.webapp.errorlog import (
    LAZR_OOPS_USER_REQUESTED_KEY,
    maybe_record_user_requested_oops,
    OopsNamespace,
    )
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    ANONYMOUS,
    login,
    logout,
    TestCase,
    )


class TestUserRequestedOops(TestCase):
    """Test the functions related to user requested oopses."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        login(ANONYMOUS)

    def tearDown(self):
        logout()
        TestCase.tearDown(self)

    def test_none_requested(self):
        # If an oops was not requested, then maybe_record_user_requested_oops
        # does not record an oops.
        oops_id = maybe_record_user_requested_oops()
        self.assertIs(None, oops_id)
        request = get_current_browser_request()
        self.assertIs(None, request.oopsid)

    def test_annotation_key(self):
        # The request for an oops is stored in the request annotations.  If a
        # user request oops is recorded, the oops id is returned, and also
        # stored in the request.
        request = get_current_browser_request()
        request.annotations[LAZR_OOPS_USER_REQUESTED_KEY] = True
        oops_id = maybe_record_user_requested_oops()
        self.assertIsNot(None, oops_id)
        self.assertEqual(oops_id, request.oopsid)

    def test_existing_oops_stops_user_requested(self):
        # If there is already an existing oops id in the request, then the
        # user requested oops is ignored.
        request = get_current_browser_request()
        request.oopsid = "EXISTING"
        request.annotations[LAZR_OOPS_USER_REQUESTED_KEY] = True
        oops_id = maybe_record_user_requested_oops()
        self.assertIs(None, oops_id)
        self.assertEqual("EXISTING", request.oopsid)

    def test_OopsNamespace_traverse(self):
        # The traverse method of the OopsNamespace sets the request
        # annotation, and returns the context that it was created with.
        request = get_current_browser_request()
        self.assertIs(
            None, request.annotations.get(LAZR_OOPS_USER_REQUESTED_KEY))
        context = object()
        namespace = OopsNamespace(context, request)
        result = namespace.traverse("name", None)
        self.assertIs(context, result)
        self.assertTrue(request.annotations.get(LAZR_OOPS_USER_REQUESTED_KEY))
