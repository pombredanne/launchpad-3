# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Mirror source content interfaces."""

__metaclass__ = type

__all__ = [
    'IMirrorSourceContent',
    ]

from zope.schema import Int
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IMirrorSourceContent(Interface):
    """The Mirror Source Content Object"""

    mirror = Int(title=_("Mirror"), required=True,
                 description=_("The Mirror where this content is."))
    distrorelease = Int(title=_("Distrorelease"), required=True,
                        description=_("The content's Distro Release"))
    component = Int(title=_("Component"), required=True,
                        description=_("The content's Component"))

