# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Browser views for archivepermission."""

__metaclass__ = type

__all__ = [
    'ArchivePermissionUrl',
    ]

from zope.interface import implements

from canonical.launchpad.webapp.interfaces import ICanonicalUrlData

class ArchivePermissionURL:
    """Dynamic URL declaration for `IArchivePermission`."""
    implements(ICanonicalUrlData)
    rootsite = None

    def __init__(self, context):
        self.context = context

    @property
    def inside(self):
        return self.context.archive

    @property
    def path(self):
        if self.context.permission == ArchivePermission.UPLOAD:
            type = "+upload"
        elif self.context.permission == ArchivePermission.QUEUE_ADMIN:
            type = "+queue-admin"
        else:
            raise AssertionError, (
                "Unknown permission type %s" % self.context.permission)

        username = self.context.person.name

        if self.component is not None:
            item = self.component.name
        elif self.sourcepackagename is not None:
            item = self.sourcepackagename.name
        else:
            raise AssertionError, (
                "One of component or sourcepackagename should be set")

        return u"%s/%s.%s" % (type, username, item)
