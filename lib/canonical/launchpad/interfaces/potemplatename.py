
from zope.interface import Interface, Attribute

class IPOTemplateName(Interface):
    """A PO template name that groups PO templates with the same name."""

    name = Attribute("The name.  For example 'nautilus'.")

    title = Attribute("The title to use while rendering a view.")

    description = Attribute("A brief description to show when showing it.")

    potemplates = Attribute("The list of PO templates that have this name.")
