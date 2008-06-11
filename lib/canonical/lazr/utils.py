# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Various utility functions."""

__metaclass__ = type
__all__ = [
    'smartquote',
    'safe_hasattr',
    ]


import re

missing = object()


def smartquote(str):
    """Return a copy of the string, with typographical quote marks applied."""
    str = unicode(str)
    str = re.compile(u'(^| )(")([^" ])').sub(u'\\1\u201c\\3', str)
    str = re.compile(u'([^ "])(")($|[\s.,;:!?])').sub(u'\\1\u201d\\3', str)
    return str


def safe_hasattr(ob, name):
    """hasattr() that doesn't hide exceptions."""
    return getattr(ob, name, missing) is not missing

