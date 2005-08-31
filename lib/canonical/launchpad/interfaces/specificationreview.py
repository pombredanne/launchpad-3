# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Specification queueing interfaces. It is possible to put a specification
into somebody's queue, along with a message telling that person what they
are supposed to do with that spec."""

__metaclass__ = type

__all__ = [
    'ISpecificationReview',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, Int, Text
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class ISpecificationReview(Interface):
    """The queue entry for a specification on a person, including a message
    from the person who put it in their queue."""

    reviewer = Choice(title=_('Reviewer'), required=True,
        vocabulary='ValidPersonOrTeam', readonly=True,
        description=_("Select the person who you would like to review "
        "this specification."))
    requestor = Int(title=_("The person who requested this review."),
        required=True)
    specification = Int(title=_('Specification ID'), required=True,
        readonly=True)
    queuemsg = Text(title=_("Message"), required=False,
        description=_("A brief message for the person that you are "
        "asking to look at this spec. Tell them why you are putting this "
        "spec in their queue."))


