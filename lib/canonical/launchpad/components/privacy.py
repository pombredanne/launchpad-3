# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Adapters related to object privacy."""

__metaclass__ = type
__all__ = []

from zope.security.interfaces import ForbiddenAttribute


class ObjectPrivacy:
    """Adapt Interface to IObjectPrivacy."""

    def __init__(self, object):
        try:
            self.is_private = object.private
        except (AttributeError, ForbiddenAttribute):
            self.is_private = False
        self.privacy_info = ''
