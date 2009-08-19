# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The primary context interface."""

__metaclass__ = type
__all__ = [
    'IRootContext',
    ]


from zope.interface import Interface


class IRootContext(Interface):
    """Something that is an object off the Launchpad root."""
