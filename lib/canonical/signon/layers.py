# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Layers used by the SSO server."""

__metaclass__ = type

from zope.publisher.interfaces.browser import (
    IBrowserRequest, IDefaultBrowserLayer)


class OpenIDLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The `OpenID` layer."""

