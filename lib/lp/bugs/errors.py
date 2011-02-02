# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Errors used in the lp/bugs modules."""

__metaclass__ = type
__all__ = [
    'InvalidBugTargetType',
    'InvalidDuplicateValue',
]

from lazr.restful.declarations import webservice_error

from canonical.launchpad.validators import LaunchpadValidationError


class InvalidBugTargetType(Exception):
    """Bug target's type is not valid."""
    webservice_error(400)


class InvalidDuplicateValue(LaunchpadValidationError):
    """A bug cannot be set as the duplicate of another."""
    webservice_error(417)
