# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Featured project interfaces."""

__metaclass__ = type

__all__ = [
    'IFeaturedProject',
    ]

from zope.interface import Attribute, Interface


class IFeaturedProject(Interface):
    """A featured project name."""

    id = Attribute("The unique ID of this featured project")
    name = Attribute("The name of the featured project")

    def destroySelf():
        """Remove this project from the featured project list."""

