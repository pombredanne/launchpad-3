# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interfaces having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'IPersonResource',
    ]


from canonical.launchpad.interfaces.person import PersonNameField
from canonical.lazr.interfaces import IEntryResource

class IPersonResource(IEntryResource):
    """The part of a person that we expose through the web service."""

    name = PersonNameField()
