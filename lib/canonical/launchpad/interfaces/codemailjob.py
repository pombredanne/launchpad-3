# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interfaces including and related to ICodeMailJob."""

__metaclass__ = type

__all__ = [
    'ICodeMailJob', 'ICodeMailJobSource'
    ]

from zope.interface import Interface
from zope.schema import (
    Datetime, Int, Object, Text, TextLine,)

from canonical.launchpad import _
from canonical.launchpad.interfaces.diff import IStaticDiff
from canonical.launchpad.interfaces.job import IJob


class ICodeMailJob(Interface):

    id = Int(title=_('ID'), required=True, readonly=True)
    job = Object(schema=IJob, required=True)
    rfc822msgid = TextLine(title=_('RFC822 Msg ID'), required=True)
    in_reply_to = TextLine(title=_('Reply-to message ID'))
    date_created = Datetime(title=_('Date Created'), required=True)
    from_address = TextLine(title=_('From address'), required=True)
    reply_to_address = TextLine(title=_('Address for replies'))
    to_address = TextLine(title=_('To address'), required=True)
    subject = TextLine(title=_('Subject'), required=True)
    body = Text(title=_('Body text'), required=True)
    footer = Text(title=_('Footer'), )
    rationale = TextLine(title=_('Machine-readable rationale for message'))
    branch_url = TextLine(title=_('URL of a related branch'))
    branch_project_name = TextLine(title=_("Branch's project's name"))
    static_diff = Object(schema=IStaticDiff)


class ICodeMailJobSource(Interface):

    def create():
        """Create a CodeMailJob."""
