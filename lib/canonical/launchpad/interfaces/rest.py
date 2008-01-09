# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interfaces having to do with Launchpad people."""

__metaclass__ = type
__all__ = [
    'IPersonResource',
    ]


from canonical.interfaces.person import PersonNameField


class IPersonResource(IResource):
    """The part of a person that we expose through the web service."""

    name = PersonNameField()
