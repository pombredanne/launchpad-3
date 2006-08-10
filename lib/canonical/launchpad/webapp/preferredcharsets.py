# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Preferred charsets."""

__metaclass__ = type

__all__ = ['Utf8PreferredCharsets']

from zope.component import adapts
from zope.interface import implements
from zope.i18n.interfaces import IUserPreferredCharsets
from zope.publisher.interfaces.http import IHTTPRequest


class Utf8PreferredCharsets:
    """An IUserPreferredCharsets which always chooses utf-8."""

    adapts(IHTTPRequest)
    implements(IUserPreferredCharsets)

    def __init__(self, request):
        self.request = request

    def getPreferredCharsets(self):
        """See IUserPreferredCharsets."""
        return ['utf-8']
