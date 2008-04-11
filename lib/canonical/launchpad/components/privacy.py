# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Adapters related to object privacy."""

__metaclass__ = type
__all__ = []

from zope.security.proxy import removeSecurityProxy


class ObjectPrivacy:
    """Generic adapter for IObjectPrivacy.

    It relies on the fact that all our objects supporting privacy use an
    attribute named 'private' to represent that fact.
    """

    def __init__(self, object):
        try:
            self.is_private = removeSecurityProxy(object).private
        except AttributeError:
            self.is_private = False
        self.privacy_info = ''
