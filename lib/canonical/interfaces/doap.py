#
# DOAP Interfaces
#
# Please use these as follows:
#
#   import canonical.interfaces
#   ... canonical.interfaces.IProject
#

# arch-tag: 475fb26f-ba51-4e80-a1d1-c5c57b728908

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('doap')
from zope.interface import Interface, Attribute

from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.app.form.browser.interfaces import IAddFormCustomization


__all__ = ['IDOAPApplication', 'IProjectContainer']

class IDOAPApplication(Interface):
    """DOAP application class."""

# Interfaces for containers

class IProjectContainer(Interface):
    """A container for IProject objects."""

    def __getitem__(key):
        """Get a Project by name."""

    def __iter__():
        """Iterate through Projects."""

    def search(querytext):
        """Search through Projects."""

