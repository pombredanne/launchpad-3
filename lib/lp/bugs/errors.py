# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Errors used in the lp/bugs modules."""

__metaclass__ = type
__all__ = [
    'InvalidBugTargetType',
    'InvalidDuplicateValue',
    'SubscriptionPrivacyViolation',
]

import httplib

from lazr.restful.declarations import error_status

from lp.app.validators import LaunchpadValidationError


@error_status(httplib.BAD_REQUEST)
class InvalidBugTargetType(Exception):
    """Bug target's type is not valid."""


@error_status(httplib.EXPECTATION_FAILED)
class InvalidDuplicateValue(LaunchpadValidationError):
    """A bug cannot be set as the duplicate of another."""

@error_status(httplib.BAD_REQUEST)
class SubscriptionPrivacyViolation(Exception):
    """The subscription would violate privacy policies."""
