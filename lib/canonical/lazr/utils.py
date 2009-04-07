# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Various utility functions."""

__metaclass__ = type
__all__ = [
    'camelcase_to_underscore_separated',
    'get_current_browser_request',
    'safe_js_escape',
    'safe_hasattr',
    'smartquote',
    ]


import cgi
import re

from simplejson import encoder


missing = object()


def camelcase_to_underscore_separated(name):
    """Convert 'ACamelCaseString' to 'a_camel_case_string'"""
    def prepend_underscore(match):
        return '_' + match.group(1)
    return re.sub('\B([A-Z])', prepend_underscore, name).lower()


def safe_hasattr(ob, name):
    """hasattr() that doesn't hide exceptions."""
    return getattr(ob, name, missing) is not missing


def smartquote(str):
    """Return a copy of the string, with typographical quote marks applied."""
    str = unicode(str)
    str = re.compile(u'(^| )(")([^" ])').sub(u'\\1\u201c\\3', str)
    str = re.compile(u'([^ "])(")($|[\s.,;:!?])').sub(u'\\1\u201d\\3', str)
    return str


def safe_js_escape(text):
    """Return the given text escaped for use in Javascript code.

    This will also perform a cgi.escape() on the given text.
    """
    return encoder.encode_basestring(cgi.escape(text, True))


def get_current_browser_request():
    """Return the current browser request, looked up from the interaction.

    If there is no suitable request, then return None.

    Returns only requests that provide IHTTPApplicationRequest.
    """
    from zope.security.management import queryInteraction
    from zope.publisher.interfaces.http import IHTTPApplicationRequest
    interaction = queryInteraction()
    requests = [
        participation
        for participation in interaction.participations
        if IHTTPApplicationRequest.providedBy(participation)
        ]
    if not requests:
        return None
    assert len(requests) == 1, (
        "We expect only one IHTTPApplicationRequest in the interaction."
        " Got %s." % len(requests))
    return requests[0]
