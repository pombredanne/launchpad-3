
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class IDistroReleaseQueue(Interface):
    """A Queue item for Lucille"""

    id = Int(
            title = _("ID"), required = True, readonly = True,
            )

    status = Int(
            title = _("Queue status"), required = True, readonly = False,
            )

    distrorelease = Int(
            title = _("Distribution release"), required = True, readonly = False,
            )

class IDistroReleaseQueueBuild(Interface):
    """A Queue item's related builds (for Lucille)"""

    id = Int(
            title = _("ID"), required = True, readonly = True,
            )


    distroreleasequeue = Int(
            title = _("Distribution release queue"), required = True,
            readonly = False,
            )

    build = Int(
            title = _("The related build"), required = True, readonly = False,
            )

class IDistroReleaseQueueSource(Interface):
    """A Queue item's related sourcepackagereleases (for Lucille)"""

    id = Int(
            title = _("ID"), required = True, readonly = True,
            )


    distroreleasequeue = Int(
            title = _("Distribution release queue"), required = True,
            readonly = False,
            )

    sourcepackagerelease = Int(
            title = _("The related source package release"), required = True,
            readonly = False,
            )

