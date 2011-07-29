# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Security adapters for the soyuz module."""

__metaclass__ = type
__all__ = [
    'ViewProcessor',
    'ViewProcessorFamily',
    ]

from lp.app.security import AnonymousAuthorization
from lp.soyuz.interfaces.processor import (
    IProcessor,
    IProcessorFamily,
    )


class ViewProcessor(AnonymousAuthorization):
    """Anyone can view an `IProcessor`."""
    usedfor = IProcessor


class ViewProcessorFamily(AnonymousAuthorization):
    """Anyone can view an `IProcessorFamily`."""
    usedfor = IProcessorFamily
