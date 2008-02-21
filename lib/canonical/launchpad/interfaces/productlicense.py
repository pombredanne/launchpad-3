# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Product license interface."""

__metaclass__ = type

__all__ = ['IProductLicense']

from zope.interface import Interface, Attribute

class IProductLicense(Interface):
    """A link between a product and a license."""

    product = Attribute("Product which has a license")
    license = Attribute("License use by all or part of a project")
