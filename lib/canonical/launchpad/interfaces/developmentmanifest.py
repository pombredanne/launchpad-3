# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Interfaces for a Development Manifest."""

__metaclass__ = type

__all__ = [
    'IDevelopmentManifest',
    ]

from zope.i18nmessageid import MessageIDFactory

from zope.interface import Interface, Attribute

from zope.schema import Datetime, Int, Choice, Text, TextLine

from canonical.launchpad.interfaces import IHasOwner

_ = MessageIDFactory('launchpad')


class IDevelopmentManifest(IHasOwner):
    """A Development Manifest."""

    owner = Choice(title=_('Owner'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')
    distrorelease = Choice(title=_('Distribution Release'), required=False,
        vocabulary='DistroRelease', description=_('Select '
        'the distribution release for which this package is being '
        'developed.'))
    sourcepackagename = Choice(title=_('Source Package'), required=False,
        vocabulary='SourcePackageName', description=_('The source package '
        'name. We will list your development work on the web site pages '
        'for this source package so that other people can find your '
        'versions of the package.'))
    manifest = Attribute("The Manifest.")
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)



