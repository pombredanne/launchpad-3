# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces related to licenses."""

__metaclass__ = type

__all__ = [
    'ILicense',
    'ILicenseSet',
    ]

from zope.schema import Datetime, Int, Text
from zope.interface import Interface
from canonical.launchpad import _

class ILicenseSet(Interface):
    """A set of licenses."""

    def __iter__():
        """Return an iterator over all the licenses."""

    def get(bugid):
        """Get a specific license by its ID.

        If it can't be found, NotFoundError will be raised.
        """

class ILicense(Interface):
    """The license entry."""

    id = Int(
        title=_('License ID'), required=True, readonly=True)
    legalese = Text(
        title=_('Legalese'), required=True,
        description=_("""A description of the license."""))
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)
