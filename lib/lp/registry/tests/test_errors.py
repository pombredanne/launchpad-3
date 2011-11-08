# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for registry errors."""


__metaclass__ = type


from httplib import (
    BAD_REQUEST,
    CONFLICT,
    FORBIDDEN,
    UNAUTHORIZED,
    )

from canonical.testing.layers import FunctionalLayer
from lp.registry.errors import (
    CannotTransitionToCountryMirror,
    DeleteSubscriptionError,
    DistroSeriesDifferenceError,
    JoinNotAllowed,
    NameAlreadyTaken,
    OpenTeamLinkageError,
    PPACreationError,
    PrivatePersonLinkageError,
    TeamMembershipTransitionError,
    TeamSubscriptionPolicyError,
    UserCannotChangeMembershipSilently,
    UserCannotSubscribePerson,
    )
from lp.testing import TestCase
from lp.testing.views import create_webservice_error_view


class TestWebServiceErrors(TestCase):
    """ Test that errors are correctly mapped to HTTP status codes."""

    layer = FunctionalLayer

    def test_OpenTeamLinkageError_forbidden(self):
        error_view = create_webservice_error_view(OpenTeamLinkageError())
        self.assertEqual(FORBIDDEN, error_view.status)

    def test_PersonLinkageError_forbidden(self):
        error_view = create_webservice_error_view(PrivatePersonLinkageError())
        self.assertEqual(FORBIDDEN, error_view.status)

    def test_PPACreationError_bad_request(self):
        error_view = create_webservice_error_view(PPACreationError())
        self.assertEqual(BAD_REQUEST, error_view.status)

    def test_JoinNotAllowed_bad_request(self):
        error_view = create_webservice_error_view(JoinNotAllowed())
        self.assertEqual(BAD_REQUEST, error_view.status)

    def test_TeamSubscriptionPolicyError_forbidden(self):
        error_view = create_webservice_error_view(
            TeamSubscriptionPolicyError())
        self.assertEqual(FORBIDDEN, error_view.status)

    def test_TeamMembershipTransitionError_bad_request(self):
        error_view = create_webservice_error_view(
            TeamMembershipTransitionError())
        self.assertEqual(BAD_REQUEST, error_view.status)

    def test_DistroSeriesDifferenceError_bad_request(self):
        error_view = create_webservice_error_view(
            DistroSeriesDifferenceError())
        self.assertEqual(BAD_REQUEST, error_view.status)

    def test_DeleteSubscriptionError_bad_request(self):
        error_view = create_webservice_error_view(DeleteSubscriptionError())
        self.assertEqual(BAD_REQUEST, error_view.status)

    def test_UserCannotSubscribePerson_bad_request(self):
        error_view = create_webservice_error_view(UserCannotSubscribePerson())
        self.assertEqual(UNAUTHORIZED, error_view.status)

    def test_CannotTransitionToCountryMirror_bad_request(self):
        error_view = create_webservice_error_view(
            CannotTransitionToCountryMirror())
        self.assertEqual(BAD_REQUEST, error_view.status)

    def test_UserCannotChangeMembershipSilently_bad_request(self):
        error_view = create_webservice_error_view(
            UserCannotChangeMembershipSilently())
        self.assertEqual(UNAUTHORIZED, error_view.status)

    def test_NameAlreadyTaken_bad_request(self):
        error_view = create_webservice_error_view(NameAlreadyTaken())
        self.assertEqual(CONFLICT, error_view.status)
