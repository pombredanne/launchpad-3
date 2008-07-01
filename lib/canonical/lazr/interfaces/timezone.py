# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'ITimezoneNameVocabulary',
    ]

from zope.interface import Interface


class ITimezoneNameVocabulary(Interface):
    """A vocabulary of timezone names."""
