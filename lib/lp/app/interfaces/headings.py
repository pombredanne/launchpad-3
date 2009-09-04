# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for headings and breadcrumbs."""

__metaclass__ = type
__all__ = [
    'IEditableContextTitle',
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


class IEditableContextTitle(Interface):
    """Interface specifying that the context has an editable title."""

    def title_edit_widget():
        """Return the HTML of the editable title widget."""
