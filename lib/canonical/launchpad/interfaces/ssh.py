# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.schema import Int, TextLine
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

__all__ = ['ISSHKey']

class ISSHKey(Interface):
    """SSH public key"""
    id = Int(title=_("Database ID"), required=True, readonly=True)
    person = Int(title=_("Owner"), required=True, readonly=True)
    keytype = TextLine(title=_("Key type"), required=True)
    keytext = TextLine(title=_("Key text"), required=True)
    comment = TextLine(title=_("Comment describing this key"), required=True)

