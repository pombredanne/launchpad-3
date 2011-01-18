# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Adapters for registry objects for the webservice."""

__metaclass__ = type
__all__ = []

from lazr.restful.interfaces import (
    IFieldHTMLRenderer,
    IWebServiceClientRequest,
    )
from zope import component
from zope.interface import (
    implementer,
    Interface,
    )

from lp.app.browser.tales import PersonFormatterAPI
from lp.services.fields import IPersonChoice


@component.adapter(Interface, IPersonChoice, IWebServiceClientRequest)
@implementer(IFieldHTMLRenderer)
def person_renderer(context, field, request):
    """Render a person as a link to the person."""

    def render(value):
        if value is None:
            return ''
        else:
            link = PersonFormatterAPI(value).link(None)
            # This span is required for now as it is used in the parsing of
            # the dt list returned by default as the xhtml representation.  To
            # remove this, you need to fix the javascript parsing in
            # lp.app.javascript.picker (we think).
            return '<span>%s</span>' % link
    return render
