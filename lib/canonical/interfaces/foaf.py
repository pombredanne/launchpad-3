#
# FOAF Interfaces
#
# Please use these as follows:
#
#   import canonical.interfaces
#   ... canonical.interfaces.IProject
#
# arch-tag: BBA2D0BE-1137-11D9-B61B-000A95954466

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('foaf')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization


__all__ = ['IFOAFApplication', 'IProjectContainer']

class IFOAFApplication(Interface):
    """FOAF application class."""

# Interfaces for containers

class IProjectContainer(Interface):
    """A container for IProject objects."""

    def __getitem__(key):
        """Get a Project by name."""

    def __iter__():
        """Iterate through Projects."""

    def search(querytext):
        """Search through Projects."""

