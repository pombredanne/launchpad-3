
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class IPackagePublishing(Interface):
    """A binary package publishing record."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    binarypackage = Int(
            title=_('The binary package being published'), required=False,
            readonly=False,
            )
    distroarchrelease = Int(
            title=_('The distroarchrelease being published into'),
            required=False, readonly=False,
            )
    component = Int(
            title=_('The component being published into'),
            required=False, readonly=False,
            )
    section = Int(
            title=_('The section being published into'),
            required=False, readonly=False,
            )
    priority = Int(
            title=_('The priority being published into'),
            required=False, readonly=False,
            )
    scheduleddeletiondate = Datetime(
            title=_('The date on which this record is scheduled for deletion'),
            required=False, readonly=False,
            )
    status = Int(
            title=_('The status of this publishing record'),
            required=False, readonly=False,
            )
    
class ISourcePackagePublishing(Interface):
    """A source package publishing record."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    sourcepackagerelease = Int(
            title=_('The source package release being published'),
            required=False, readonly=False,
            )
    status = Int(
            title=_('The status of this publishing record'),
            required=False, readonly=False,
            )
    distrorelease = Int(
            title=_('The distrorelease being published into'),
            required=False, readonly=False,
            )
    component = Int(
            title=_('The component being published into'),
            required=False, readonly=False,
            )
    section = Int(
            title=_('The section being published into'),
            required=False, readonly=False,
            )
    datepublished = Datetime(
            title=_('The date on which this record was published'),
            required=False, readonly=False,
            )
    scheduleddeletiondate = Datetime(
            title=_('The date on which this record is scheduled for deletion'),
            required=False, readonly=False,
            )
    
class ISourcePackageFilesToPublish(Interface):
    """Source package release files due for publishing"""

    drd = Int(
            title=_('Distribution'), required=True, readonly=True,
            )

    sppid = Int(
            title=_('Sourcepackage publishing record id'), required=True,
            readonly=True,
            )

    pfalias = Int(
            title=_('Sourcepackage release file alias'), required=True,
            readonly=True,
            )
 
    lfaname = TextLine(
            title=_('File name'), required=True, readonly=True,
            )

    cname = TextLine(
            title=_('Component name'), required=True, readonly=True,
            )

    spname = TextLine(
            title=_('Source package name'), required=True, readonly=True,
            )

class IBinaryPackageFilesToPublish(Interface):
    """Source package release files due for publishing"""

    drd = Int(
            title=_('Distribution'), required=True, readonly=True,
            )

    ppid = Int(
            title=_('Package publishing record id'), required=True,
            readonly=True,
            )

    pfalias = Int(
            title=_('Binarypackage file alias'), required=True,
            readonly=True,
            )
 
    lfaname = TextLine(
            title=_('File name'), required=True, readonly=True,
            )

    cname = TextLine(
            title=_('Component name'), required=True, readonly=True,
            )

    spname = TextLine(
            title=_('Source package name'), required=True, readonly=True,
            )

class IPublishedSourcePackageOverrides(Interface):
    """Source package overrides published and thus due for putting on disk"""

    drname = TextLine(
            title=_('Distro Release name'), required=True, readonly=True,
            )
    spname = TextLine(
            title=_('Binary package name'), required=True, readonly=True,
            )
    cname = TextLine(
            title=_('Component name'), required=True, readonly=True,
            )
    sname = TextLine(
            title=_('Section name'), required=True, readonly=True,
            )
    
    distro = Int(
            title=_('Distribution ID'), required=True, readonly=True,
            )



class IPublishedBinaryPackageOverrides(Interface):
    """Binary package overrides published and thus due for putting on disk"""

    drname = TextLine(
            title=_('Distro Release name'), required=True, readonly=True,
            )
    bpname = TextLine(
            title=_('Binary package name'), required=True, readonly=True,
            )
    cname = TextLine(
            title=_('Component name'), required=True, readonly=True,
            )
    sname = TextLine(
            title=_('Distro Release name'), required=True, readonly=True,
            )
    
    priority = Int(
            title=_('Priority'), required=True, readonly=True,
            )
    
    distro = Int(
            title=_('Distribution ID'), required=True, readonly=True,
            )
