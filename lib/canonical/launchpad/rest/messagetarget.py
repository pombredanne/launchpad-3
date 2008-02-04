# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad message targets."""

__metaclass__ = type
__all__ = [
    'IMessageTargetEntry',
    ]

from zope.schema import Object
from canonical.lazr.interfaces import IEntry

from canonical.launchpad.interfaces import IMessage
from canonical.lazr.rest.schema import CollectionField

class IMessageTargetEntry(IEntry):
    """The part of a message target that we expose through the web service.
    """

    messages = CollectionField(value_type=Object(schema=IMessage))
    followup_subject = TextLine(
        title=_(u"The likely subject of the next message."))
