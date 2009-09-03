# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The primary context interface."""

__metaclass__ = type
__all__ = [
    'IIndexView',
    'IRootContext',
    ]


from zope.interface import Attribute, Interface


class IRootContext(Interface):
    """Something that is an object off the Launchpad root."""

    title = Attribute('The title of the root context object.')


class IIndexView(Interface):
    """The index view of the current context."""

    title = Attribute('The title of the context object.')
