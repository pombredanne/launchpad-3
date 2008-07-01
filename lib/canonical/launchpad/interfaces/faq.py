# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interface for FAQ document."""

__metaclass__ = type

__all__ = [
    'IFAQ',
    'IFAQSet',
    ]

from zope.interface import Attribute
from zope.schema import (
     Datetime,  Int, Object, Text, TextLine)

from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice, Title
from canonical.launchpad.interfaces.faqcollection import IFAQCollection
from canonical.launchpad.interfaces.faqtarget import IFAQTarget
from canonical.launchpad.interfaces.launchpad import IHasOwner


class IFAQ(IHasOwner):
    """A document containing the answer to a commonly asked question.

    The answer can be in the document itself or can be hosted on a separate
    web site and referred to by URL.
    """

    id = Int(
        title=_('FAQ Number'),
        description=_('The unique number identifying the FAQ in Launchpad.'),
        required=True, readonly=True)

    title = Title(
        title=_('Title'),
        description=_('The title describing the FAQ, often a question.'),
        required=True)

    keywords = TextLine(
        title=_('Keywords'),
        description=_('One or more terms that relate to this FAQ.'),
        required=False)

    content = Text(
        title=_('Content'),
        description=_(
            'The answer to the question in plain text. You may choose to '
            'include a URL to an external FAQ.'),
        required=True)

    date_created = Datetime(title=_('Created'), required=True, readonly=True)

    last_updated_by = PublicPersonChoice(
        title=_('Last Updated By'),
        description=_('The last person who modified the document.'),
        vocabulary='ValidPersonOrTeam', required=False)

    date_last_updated = Datetime(title=_('Last Updated'), required=False)

    target = Object(
        title=_('Target'),
        description=_('Product or distribution containing this FAQ.'),
        schema=IFAQTarget,
        required=True)

    related_questions = Attribute(
        _('The set of questions linked to this FAQ.'))


class IFAQSet(IFAQCollection):
    """`IFAQCollection` of all the FAQs existing in Launchpad.

    This interface is provided by a global utility object which can
    be used to search or retrieve any FAQ registered in Launchpad.
    """
