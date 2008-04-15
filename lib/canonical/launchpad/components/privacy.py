# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Adapters related to object privacy."""

__metaclass__ = type
__all__ = []

from zope.security.proxy import removeSecurityProxy
from canonical.launchpad.webapp.badge import HasBadgeBase


class ObjectPrivacy(HasBadgeBase):
    """Generic adapter for IObjectPrivacy.

    It relies on the fact that all our objects supporting privacy use an
    attribute named 'private' to represent that fact.
    """
    badges = 'private',
    badge_titles = {'private': 'Private'}

    def __init__(self, object):
        try:
            self.is_private = removeSecurityProxy(object).private
        except AttributeError:
            self.is_private = False
