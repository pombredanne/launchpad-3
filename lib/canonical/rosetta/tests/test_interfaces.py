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

def test_verify_sql_projects():
    '''
    >>> from canonical.rosetta.interfaces import IProjects
    >>> from canonical.rosetta.sql import RosettaProjects
    >>> verifyClass(IProjects, RosettaProjects)
    True
    '''

def test_verify_sql_project():
    '''
    >>> from canonical.rosetta.interfaces import IProject
    >>> from canonical.rosetta.sql import RosettaProject
    >>> verifyClass(IProject, RosettaProject)
    True
    '''

def test_verify_sql_product():
    '''
    >>> from canonical.rosetta.interfaces import IProduct
    >>> from canonical.rosetta.sql import RosettaProduct
    >>> verifyClass(IProduct, RosettaProduct)
    True
    '''

def test_verify_sql_potemplate():
    '''
    >>> from canonical.rosetta.interfaces import IPOTemplate
    >>> from canonical.rosetta.sql import RosettaPOTemplate
    >>> verifyClass(IPOTemplate, RosettaPOTemplate)
    True
    '''

def test_verify_sql_pofile():
    '''
    >>> from canonical.rosetta.interfaces import IPOFile
    >>> from canonical.rosetta.sql import RosettaPOFile
    >>> verifyClass(IPOFile, RosettaPOFile)
    True
    '''

def test_verify_sql_pomessageset():
    '''
    >>> from canonical.rosetta.interfaces import IPOMessageSet
    >>> from canonical.rosetta.ipofile import IPOMessage
    >>> from canonical.rosetta.sql import RosettaPOMessageSet
    >>> verifyClass(IPOMessageSet, RosettaPOMessageSet)
    True
    >>> verifyClass(IPOMessage, RosettaPOMessageSet)
    True
    '''

def test_verify_sql_pomessageidsighting():
    '''
    >>> from canonical.rosetta.interfaces import IPOMessageIDSighting
    >>> from canonical.rosetta.sql import RosettaPOMessageIDSighting
    >>> verifyClass(IPOMessageIDSighting, RosettaPOMessageIDSighting)
    True
    '''

def test_verify_sql_pomessageid():
    '''
    >>> from canonical.rosetta.interfaces import IPOMessageID
    >>> from canonical.rosetta.sql import RosettaPOMessageID
    >>> verifyClass(IPOMessageID, RosettaPOMessageID)
    True
    '''

def test_verify_sql_potranslationsighting():
    '''
    >>> from canonical.rosetta.interfaces import IPOTranslationSighting
    >>> from canonical.rosetta.sql import RosettaPOTranslationSighting
    >>> verifyClass(IPOTranslationSighting, RosettaPOTranslationSighting)
    True
    '''

def test_verify_sql_potranslation():
    '''
    >>> from canonical.rosetta.interfaces import IPOTranslation
    >>> from canonical.rosetta.sql import RosettaPOTranslation
    >>> verifyClass(IPOTranslation, RosettaPOTranslation)
    True
    '''

def test_verify_sql_language():
    '''
    >>> from canonical.rosetta.interfaces import ILanguage
    >>> from canonical.rosetta.sql import RosettaLanguage
    >>> verifyClass(ILanguage, RosettaLanguage)
    True
    '''

def test_verify_sql_person():
    '''
    >>> from canonical.rosetta.interfaces import IPerson
    >>> from canonical.rosetta.sql import Person
    >>> verifyClass(IPerson, Person)
    True
    '''

def test_verify_sql_languages():
    """
    >>> from canonical.rosetta.interfaces import ILanguages
    >>> from canonical.rosetta.sql import RosettaLanguages
    >>> verifyClass(ILanguages, RosettaLanguages)
    True
    """


def test_suite():
    suite = DocTestSuite()
    return suite

if __name__ == '__main__':
    unittest.main()

