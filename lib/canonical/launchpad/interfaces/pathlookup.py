# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

__metaclass__ = type
__all__ = ['IPathLookupError',
           'IPathStepRequiredError',
           'IPathStepNotFoundError']

from zope.interface import (
    Attribute,
    Interface,
    )


class IPathLookupError(Interface):
    """Something went wrong when looking up the path."""


class IPathStepRequiredError(IPathLookupError):
    """A step of the path is missing.

    For example the '/products' is missing a product.
    """
    missing_types = Attribute(
        """A list of types that was expected.

        For example if the path was missing either a product release, or
        a product series, missing_types should consist of
        [IProductRelase, IProductSeries].
        """)

class IPathStepNotFoundError(IPathLookupError):
    """A step of the path is not found.

    For example if 'foo' isn't a product, and '/product/foo' is looked
    up, this error should be raised telling that 'foo' couldn't be
    found.
    """
    step = Attribute("The name of the step that wasn't found.")
    notfound_types = Attribute(
        """A list of types that was expected.

        For example if 'foo' wasn't found, and 'foo' should have been
        either  a product release, or a product series, notfound_types
        should consist of [IProductRelase, IProductSeries].
        """)
