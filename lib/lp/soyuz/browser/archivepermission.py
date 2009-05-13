# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Browser views for archivepermission."""

__metaclass__ = type

__all__ = [
    'ArchivePermissionUrl',
    ]

from zope.interface import implements

from lp.soyuz.interfaces.archivepermission import (
    ArchivePermissionType)
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
        if self.context.permission == ArchivePermissionType.UPLOAD:
            perm_type = "+upload"
        elif self.context.permission == ArchivePermissionType.QUEUE_ADMIN:
            perm_type = "+queue-admin"
        else:
            raise AssertionError, (
                "Unknown permission type %s" % self.context.permission)

        username = self.context.person.name

        item = self.context.component_name
        if item is None:
            item = self.context.source_package_name
        if item is None:
            raise AssertionError, (
                "One of component or sourcepackagename should be set")

        return u"%s/%s.%s" % (perm_type, username, item)
