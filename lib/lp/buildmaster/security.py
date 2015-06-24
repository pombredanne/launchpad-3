# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Security adapters for the buildmaster package."""

__metaclass__ = type
__all__ = [
    'ViewBuilder',
    'ViewProcessor',
    ]

from lp.app.security import AnonymousAuthorization
from lp.buildmaster.interfaces.builder import IBuilder
from lp.buildmaster.interfaces.processor import IProcessor


class ViewBuilder(AnonymousAuthorization):
    """Anyone can view a `IBuilder`."""
    usedfor = IBuilder


class ViewProcessor(AnonymousAuthorization):
    """Anyone can view an `IProcessor`."""
    usedfor = IProcessor
