# Imports from zope
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

class IPackages(Interface):
    """Root object for web app."""
    binary = Attribute("Binary packages")
    source = Attribute("Source packages")

    def __getitem__(name):
        """Retrieve a package set by name."""

class IPackageSet(Interface):
    """A set of packages"""
    def __getitem__(name):
        """Retrieve a package by name."""
    def __iter__():
        """Iterate over names"""

