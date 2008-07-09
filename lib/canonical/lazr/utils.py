# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Various utility functions."""

__metaclass__ = type
__all__ = [
    'camelcase_to_underscore_separated',
    'safe_hasattr',
    'smartquote',
    ]


import re


missing = object()


def camelcase_to_underscore_separated(str):
    """Convert 'ACamelCaseString' to 'a_camel_case_string'"""
    def prepend_underscore(match):
        return '_' + match.group(1)
    return re.compile('\B([A-Z])').sub(prepend_underscore, str).lower()


def safe_hasattr(ob, name):
    """hasattr() that doesn't hide exceptions."""
    return getattr(ob, name, missing) is not missing


def smartquote(str):
    """Return a copy of the string, with typographical quote marks applied."""
    str = unicode(str)
    str = re.compile(u'(^| )(")([^" ])').sub(u'\\1\u201c\\3', str)
    str = re.compile(u'([^ "])(")($|[\s.,;:!?])').sub(u'\\1\u201d\\3', str)
    return str
