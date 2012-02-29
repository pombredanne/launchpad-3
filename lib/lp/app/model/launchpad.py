# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Common implementation of interfaces.launchpad interfaces."""

__metaclass__ = type

__all__ = [
    'ExceptionPrivacy',
    'Privacy',
    ]

from zope.interface import implements
from zope.security.interfaces import (
    Forbidden,
    ForbiddenAttribute,
    Unauthorized,
    )

from lp.app.interfaces.launchpad import IPrivacy


class Privacy:
    """Represent any object as IPrivacy."""
    implements(IPrivacy)

    def __init__(self, context, private):
        self.context = context
        self.private = private


class ExceptionPrivacy(Privacy):
    """Adapt an Exception to IPrivacy."""

    def __init__(self, error):
        if isinstance(error, (Forbidden, ForbiddenAttribute, Unauthorized)):
            private = True
        else:
            private = False
        super(ExceptionPrivacy, self).__init__(error, private)
