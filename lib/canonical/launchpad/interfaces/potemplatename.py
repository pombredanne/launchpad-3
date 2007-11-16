# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

from zope.component import getUtility
from zope.interface import Interface, Attribute
from zope.schema import TextLine, Text

from canonical.launchpad import _
from canonical.launchpad.fields import ContentNameField
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.interfaces.launchpad import NotFoundError

__metaclass__ = type

__all__ = ('IPOTemplateNameSet', 'IPOTemplateName')


class POTemplateNameNameField(ContentNameField):

    errormessage = _("%s is already in use by another PO template name.")

    @property
    def _content_iface(self):
        return IPOTemplateName

    def _getByName(self, name):
        try:
            return getUtility(IPOTemplateNameSet)[name]
        except NotFoundError:
            return None


class IPOTemplateNameSet(Interface):
    """A set of POTemplateNames."""

    def __getitem__(name):
        """Return the POTemplateName with the requested name.

        If there is no POTemplateName with that name, NotFoundError exception
        is raised.
        """

    def __iter__(self):
        """Return an iterator over all POTemplateName objects."""

    def get(potemplatenameid):
        """Get a specific PO Template Name by its ID.

        If there is no POTemplateName with that ID, NotFoundError exception
        is raised.
        """

    def new(translationdomain, title, name=None, description=None):
        """Return a new created POTemplateName."""

    def search(text):
        """Return an iterator over all POTemplateName that matches the 'text'.

        The search is done in name, title, description and translationdomain
        fields.
        """

    def searchCount(text):
        """Return the number of rows that match the 'text'.

        The search is done in name, title, description and translationdomain
        fields.
        """


class IPOTemplateName(Interface):
    """A PO template name that groups PO templates with the same name."""

    id = Attribute("The id for this PO template name.")

    name = POTemplateNameNameField(
        title=_("PO Template Name"),
        description=_("For example 'nautilus'."),
        constraint=name_validator,
        required=True)

    title = TextLine(
        title=_("PO Template Name Title"),
        description=_(
            "The title to use while rendering a page related only with this "
            "template name."),
        required=True)

    description = Text(
        title=_("PO Template Name Description"),
        description=_("A brief description of the template name."),
        required=False)

    translationdomain = TextLine(
        title=_("PO Template Translation Domain"),
        description=_(
            "Used by gettext to get translations from the related templates. "
            "Usually the same as the name."),
        required=True)

    potemplates = Attribute("The list of PO templates that have this name.")
