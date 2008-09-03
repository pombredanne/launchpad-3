# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interfaces including and related to IPendingCodeMail."""

__metaclass__ = type

__all__ = [
    'IPendingCodeMail'
    ]

from zope.interface import Interface
from zope.schema import (
    Datetime, Int, Text, TextLine,)

from canonical.launchpad import _


class IPendingCodeMail(Interface):

    id = Int(title=_('ID'), required=True, readonly=True)
    rfc822msgid = TextLine(title=_('RFC822 Msg ID'), required=True)
    in_reply_to = TextLine(title=_('Reply-to message ID'))
    #date_created = Datetime(title=_('Date Created'), required=True),
    from_address = TextLine(title=_('From address'), required=True)
    to_address = TextLine(title=_('To address'), required=True)
    subject = TextLine(title=_('Subject'), required=True)
    body = Text(title=_('Body text'), required=True)
    footer = Text(title=_('Footer'), )
    rationale = TextLine(title=_('Machine-readable rationale for message'))
    branch_url = TextLine(title=_('URL of a related branch'))
