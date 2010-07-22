# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Cross application type errors for launchpad."""

__metaclass__ = type
__all__ = [
    'UserCannotUnsubscribePerson',
    ]

from zope.security.interfaces import Unauthorized

from lazr.restful.declarations import webservice_error


class UserCannotUnsubscribePerson(Unauthorized):
    """User does not have persmisson to unsubscribe person or team."""
    webservice_error(401)
