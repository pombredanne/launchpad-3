# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interfaces including and related to IJob."""

__metaclass__ = type

__all__ = [
    'IJob',
    ]


from zope.interface import Interface
from zope.schema import Datetime

from canonical.launchpad import _


class IJob(Interface):

    lease_expires = Datetime(title=_('Date Created'))
