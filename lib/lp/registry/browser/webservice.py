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
    """Render a recipe owner as a link."""

    def render(value):
        person = getattr(context, field.__name__, None)
        if person is None:
            return ''
        else:
            return (
                '<span>%s</span>' %
                PersonFormatterAPI(person).link(None))
    return render
