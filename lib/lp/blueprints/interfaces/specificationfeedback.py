# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Specification queueing interfaces. It is possible to put a specification
into somebody's queue, along with a message telling that person what they
are supposed to do with that spec."""

__metaclass__ = type

__all__ = [
    'ISpecificationFeedback',
    ]

from zope.interface import Interface
from zope.schema import (
    Int,
    Text,
    )

from canonical.launchpad import _
from lp.services.fields import PublicPersonChoice


class ISpecificationFeedback(Interface):
    """The queue entry for a specification on a person, including a message
    from the person who put it in their queue."""

    reviewer = PublicPersonChoice(
        title=_('Feedback From'), required=True,
        vocabulary='ValidPersonOrTeam', readonly=False,
        description=_("Select the person who you would like to give you "
        "some feedback on this specification."))
    requester = PublicPersonChoice(
        title=_("The person who requested this feedback."),
        vocabulary='ValidPersonOrTeam', required=True)
    specification = Int(title=_('Specification ID'), required=True,
        readonly=True)
    queuemsg = Text(title=_("Message"), required=False,
        description=_("A brief message for the person that you are "
        "asking to look at this spec. Tell them why you are putting this "
        "specification in their queue."))


