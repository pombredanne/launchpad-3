# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bugs errors."""


__metaclass__ = type


from httplib import (
    BAD_REQUEST,
    EXPECTATION_FAILED,
    )

from canonical.testing.layers import FunctionalLayer
from lp.bugs.errors import (
    InvalidBugTargetType,
    InvalidDuplicateValue,
    SubscriptionPrivacyViolation,
    )
from lp.testing import TestCase
from lp.testing.views import create_webservice_error_view


class TestWebServiceErrors(TestCase):
    """ Test that errors are correctly mapped to HTTP status codes."""

    layer = FunctionalLayer

    def test_InvalidBugTargetType_bad_rquest(self):
        error_view = create_webservice_error_view(InvalidBugTargetType())
        self.assertEqual(BAD_REQUEST, error_view.status)

    def test_InvalidDuplicateValue_expectation_failed(self):
        error_view = create_webservice_error_view(
            InvalidDuplicateValue("Dup"))
        self.assertEqual(EXPECTATION_FAILED, error_view.status)

    def test_SubscriptionPrivacyViolation_bad_request(self):
        error_view = create_webservice_error_view(
            SubscriptionPrivacyViolation())
        self.assertEqual(BAD_REQUEST, error_view.status)
