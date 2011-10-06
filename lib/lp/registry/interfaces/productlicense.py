# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Product license interface."""

__metaclass__ = type

__all__ = ['IProductLicense']

from zope.interface import (
    Attribute,
    Interface,
    )


class IProductLicense(Interface):
    """A link between a product and a license."""

    product = Attribute("Product which has a license")
    license = Attribute("License use by all or part of a project")
