# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for creating a dependency for a given specification. The
dependency is a second specification, so this is really a way of storing the
order in which specs must be implemented. No attempt is made to prevent
circular dependencies at present."""

__metaclass__ = type

__all__ = [
    'ISpecificationDependency',
    'ISpecificationDependencyRemoval',
    'SpecDependencyIsAlsoRemoval',
    ]

from zope.interface import Interface, implements
from zope.schema import Choice, Int
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')


class ISpecificationDependency(Interface):
    """A link between a specification and another specification on which it
    depends.
    """

    specification = Int(title=_('Specification ID'), required=True,
        readonly=True)
    dependency = Choice(title=_('Dependency'), required=True, readonly=True,
        description=_("Please select the specification on which this spec "
        "depends. You are saying that the current specification can only "
        "be implemented after this spec has been implemented."),
        vocabulary='Specification')


class ISpecificationDependencyRemoval(Interface):
    """A schema that exists purely to define the text and vocabulary for the
    specification dependency removal form.
    """

    specification = Int(title=_('Specification ID'), required=True,
        readonly=True)
    dependency = Choice(title=_('Dependency'), required=True, readonly=True,
        description=_("Please select the dependency you would like to "
        "remove from the list."),
        vocabulary='SpecificationDependencies')


class SpecDependencyIsAlsoRemoval:
    implements(ISpecificationDependencyRemoval)
    __used_for__ = ISpecificationDependency

    def __init__(self, specdep):
        self.specdep = specdep

    @property
    def specification(self):
        return self.specdep.specification

    @property
    def dependency(self):
        return self.specdep.dependency

