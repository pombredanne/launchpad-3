# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Queue interfaces."""

__metaclass__ = type

__all__ = [
    'IDistroReleaseQueue',
    'IDistroReleaseQueueBuild',
    'IDistroReleaseQueueSource',
    'IDistroReleaseQueueCustom',
    ]

from zope.schema import Int
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IDistroReleaseQueue(Interface):
    """A Queue item for Lucille"""

    id = Int(
            title=_("ID"), required=True, readonly=True,
            )

    status = Int(
            title=_("Queue status"), required=True, readonly=False,
            )

    distrorelease = Int(
            title=_("Distribution release"), required=True, readonly=False,
            )

    pocket = Int(
            title=_("The pocket"), required=True, readonly=False,
            )
    

class IDistroReleaseQueueBuild(Interface):
    """A Queue item's related builds (for Lucille)"""

    id = Int(
            title=_("ID"), required=True, readonly=True,
            )


    distroreleasequeue = Int(
            title=_("Distribution release queue"), required=True,
            readonly=False,
            )

    build = Int(
            title=_("The related build"), required=True, readonly=False,
            )

class IDistroReleaseQueueSource(Interface):
    """A Queue item's related sourcepackagereleases (for Lucille)"""

    id = Int(
            title=_("ID"), required=True, readonly=True,
            )


    distroreleasequeue = Int(
            title=_("Distribution release queue"), required=True,
            readonly=False,
            )

    sourcepackagerelease = Int(
            title=_("The related source package release"), required=True,
            readonly=False,
            )

class IDistroReleaseQueueCustom(Interface):
    """A Queue item's related custom format files (for uploader/queue)"""

    id = Int(
            title=_("ID"), required=True, readonly=True,
            )

    distroreleasequeue = Int(
            title=_("Distribution release queue"), required=True,
            readonly=False,
            )

    customformat = Int(
            title=_("The custom format for the file"), required=True,
            readonly=False,
            )

    libraryfilealias = Int(
            title=_("The file"), required=True, readonly=False,
            )

