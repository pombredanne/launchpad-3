# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

# Imports from zope
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


#
# Manifest Related Interfaces
#

class IManifest(Interface):
    """A Manifest. Manifests are like Arch Configs, they tell us about the
    set of branches and other elements that make up a package of code from
    upstream, or a distro package."""

    id = Int(title=_('Manifest ID'), required=True, readonly=True)

    datecreated = Datetime(title=_('Date Created'), description=_("""The
        date this manifest was created."""), required=True, readonly=True )

    uuid = TextLine(title=_('Universally Unique ID'), description=_("""A UUID
        that is guaranteed to identify this manifest uniquely."""),
        required=True, readonly=True)

