# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Interface for FAQ document."""

__metaclass__ = type

__all__ = [
    'IFAQ',
    ]

from zope.schema import (
     Choice, Datetime,  Int, Object, Text, TextLine)

from canonical.launchpad import _
from canonical.launchpad.fields import Summary, Title, URIField
from canonical.launchpad.interfaces.faqtarget import IFAQTarget
from canonical.launchpad.interfaces.launchpad import IHasOwner


class IFAQ(IHasOwner):
    """A document containing the answer to a commonly asked question.

    The answer can be in the document itself or can be hosted on a separate
    web site and referred to by URL.
    """

    id = Int(
        title=_('FAQ Number'),
        description=_('Unique number identifying the document in Launchpad.'),
        required=True, readonly=True)

    title = Title(
        title=_('Title'),
        description=_('Title describing the document content.'),
        required=True)

    summary = Summary(
        title=_('Summary'),
        description=_(
            'Short description of the issue described in the document.'),
        required=True)

    keywords = TextLine(
        title=_('Keywords'),
        description=_('List of keywords related to this document.'),
        required=False)

    content = Text(
        title=_('Content'),
        description=_('The FAQ content. This is in plain text format.'),
        required=False)

    url = URIField(
        title=_('Link'),
        description=_('A link to a web page explaining the answer in details.'
                      'Used as an alternative to entering the content.'),
        allowed_schemes=('http', 'https'),
        required=False)

    date_created = Datetime(title=_('Created'), required=True, readonly=True)

    last_updated_by = Choice(
        title=_('Last Updated By'),
        description=_('The last person who modified the document.'),
        vocabulary='ValidPersonOrTeam', required=False)

    date_last_updated = Datetime(title=_('Last Updated'), required=False)

    target = Object(
        title=_('Target'),
        description=_('Product or distribution containing this FAQ.'),
        schema=IFAQTarget,
        required=True)

