#!/usr/bin/python
#
# arch-tag: 3945d8f8-637e-45ef-a8fc-1b142bea245f

import sys
import unittest

from zope.interface.verify import verifyClass, verifyObject, BrokenImplementation
from zope.testing.doctestunit import DocTestSuite

def test_projects():
    """
    >>> from canonical.rosetta.interfaces import IProjects
    >>> from canonical.rosetta.stub import Projects, Project

    >>> projects = Projects()
    >>> isinstance(projects.__iter__().next(), Project)
    True
    """

def test_project():
    """
    >>> from canonical.rosetta.stub import Project
    >>> project = Project("a", "a", "a", "a", "a")

    >>> list(project.products())
    []
    """

def test_product():
    """
    >>> from canonical.rosetta.stub import Project, Product
    >>> project = Project("a", "a", "a", "a", "a")
    >>> product = Product(project, "a", "a", "a")
    """

def test_verify_stub():
    """
    >>> from canonical.rosetta.interfaces import IProjects, IProject, IPOTemplate
    >>> from canonical.rosetta.stub import Projects, Project, Product, POTemplate

    >>> projects = Projects()
    >>> project = projects.__iter__().next()
    >>> product = project.products().next()
    >>> potemplate = product.poTemplates().next()

    >>> verifyObject(IProjects, projects)
    True
    >>> verifyObject(IProject, project)
    True
    >>> verifyObject(IPOTemplate, potemplate)
    True
    """

def test_suite():
    suite = DocTestSuite()
    #return suite

if __name__ == '__main__':
    unittest.main()

