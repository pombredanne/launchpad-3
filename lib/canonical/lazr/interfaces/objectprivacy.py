# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'IObjectPrivacy',
    ]

from zope.interface import Interface
from zope.schema import Bool, Text

from canonical.launchpad import _


class IObjectPrivacy(Interface):
    """Privacy-related information about an object."""

    is_private = Bool(title=_("Whether access to the object is restricted."))
