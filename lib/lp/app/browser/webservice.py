# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Adapters for registry objects for the webservice."""

__metaclass__ = type
__all__ = [
    'format_text_for_web',
]

from lazr.restful.interfaces import (
    IFieldHTMLRenderer,
    IReference,
    IWebServiceClientRequest,
    )
from zope import component
from zope.interface import (
    implementer,
    Interface,
    )
from zope.schema.interfaces import IText

from lp.app.browser.stringformatter import FormattersAPI
from lp.app.browser.tales import format_link


@component.adapter(Interface, IReference, IWebServiceClientRequest)
@implementer(IFieldHTMLRenderer)
def reference_xhtml_representation(context, field, request):
    """Render an object as a link to the object."""

    def render(value):
        # The value is a webservice link to the object, we want field value.
        obj = getattr(context, field.__name__, None)
        if obj is None:
            return ''
        else:
            try:
                return format_link(obj)
            except NotImplementedError:
                return value
    return render


def format_text_for_web(value):
    """Format the string for displaying on a web page.

    Standard practice is to obfuscate the email and render as html.
    """
    if value is None:
        return ''
    nomail = FormattersAPI(value).obfuscate_email()
    return FormattersAPI(nomail).text_to_html()


@component.adapter(Interface, IText, IWebServiceClientRequest)
@implementer(IFieldHTMLRenderer)
def text_xhtml_representation(context, field, request):
    """Render text as XHTML using the webservice."""
    return format_text_for_web
