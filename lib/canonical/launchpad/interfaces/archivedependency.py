# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""ArchiveDependency interface."""

__metaclass__ = type

__all__ = [
    'IArchiveDependency',
    ]

from zope.interface import Interface, Attribute


class IArchiveDependency(Interface):
    """ArchiveDependency interface."""

    id = Attribute("The archive ID.")

    date_created = Attribute("Instant when the dependency was created.")

    archive = Attribute("Archive affected by this dependency.")

    dependency = Attribute("Dependency archive.")
