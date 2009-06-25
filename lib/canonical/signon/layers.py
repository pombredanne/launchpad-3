# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Layers used by the SSO server."""

__metaclass__ = type

from zope.publisher.interfaces.browser import (
    IBrowserRequest, IDefaultBrowserLayer)


# XXX sinzui 2008-09-04 bug=264783:
# Remove this layer.
class OpenIDLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The `OpenID` layer."""


class IdLayer(IBrowserRequest, IDefaultBrowserLayer):
    """The new OpenID `Id` layer."""


