# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Marker interfaces that define how to generate headings for a view."""

__metaclass__ = type
__all__ = [
    'IHeadingBreadcrumb',
    'IMajorHeadingView',
    ]


from zope.interface import Interface


class IMajorHeadingView(Interface):
    """This view's page should get a major heading (i.e. H1)."""


class IHeadingBreadcrumb(Interface):
    """This breadcrumb can appear in header and thereby has no facet."""
