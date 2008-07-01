
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad message targets."""

__metaclass__ = type
__all__ = [
    'IMessageTargetEntry',
    ]

from zope.schema import Object, TextLine

from canonical.lazr.fields import CollectionField
from canonical.lazr.interfaces import IEntry

from canonical.launchpad.interfaces import IMessage

class IMessageTargetEntry(IEntry):
    """The part of a message target that we expose through the web service.
    """

    messages = CollectionField(value_type=Object(schema=IMessage))

    followup_subject = TextLine(
        title=u"The likely subject of the next message.")
