#!/usr/bin/python

# YO! Generated code -- modify at your peril!

import sys
import unittest

from zope.interface.verify import verifyClass, verifyObject
from zope.testing.doctestunit import DocTestSuite

def verifySQLObject(interface, implementation):
    if hasattr(implementation, 'select'):
        return verifyObject(interface, implementation.select()[0])
    else:
        return True


from canonical.arch.sqlbase import SQLBase
from canonical.rosetta.sql import RosettaPOMessageSet, RosettaLanguage
from sqlobject import connectionForURI

SQLBase.initZopeless(connectionForURI('postgres:///launchpad_test'))

def test_verify_sql_projects():
    '''
    >>> from canonical.rosetta.interfaces import IProjects
    >>> from canonical.rosetta.sql import RosettaProjects
    >>> verifySQLObject(IProjects, RosettaProjects)
    True
    '''

def test_verify_sql_project():
    '''
    >>> from canonical.rosetta.interfaces import IProject
    >>> from canonical.rosetta.sql import RosettaProject
    >>> verifySQLObject(IProject, RosettaProject)
    True
    '''

def test_verify_sql_product():
    '''
    >>> from canonical.rosetta.interfaces import IProduct
    >>> from canonical.rosetta.sql import RosettaProduct
    >>> verifySQLObject(IProduct, RosettaProduct)
    True
    '''

def test_verify_sql_editpotemplate():
    '''
    >>> from canonical.rosetta.interfaces import IEditPOTemplate
    >>> from canonical.rosetta.sql import RosettaPOTemplate
    >>> verifySQLObject(IEditPOTemplate, RosettaPOTemplate)
    True
    '''

def test_verify_sql_editpofile():
    '''
    >>> from canonical.rosetta.interfaces import IEditPOFile
    >>> from canonical.rosetta.sql import RosettaPOFile
    >>> verifySQLObject(IEditPOFile, RosettaPOFile)
    True
    '''

def test_verify_sql_editpomessageset():
    '''
    >>> from canonical.rosetta.interfaces import IEditPOMessageSet
    >>> from canonical.rosetta.sql import RosettaPOMessageSet
    >>> verifySQLObject(IEditPOMessageSet, RosettaPOMessageSet)
    True
    '''

def test_verify_sql_editpomessageidsighting():
    '''
    >>> from canonical.rosetta.interfaces import IEditPOMessageIDSighting
    >>> from canonical.rosetta.sql import RosettaPOMessageIDSighting
    >>> verifySQLObject(IEditPOMessageIDSighting, RosettaPOMessageIDSighting)
    True
    '''

def test_verify_sql_pomessageid():
    '''
    >>> from canonical.rosetta.interfaces import IPOMessageID
    >>> from canonical.rosetta.sql import RosettaPOMessageID
    >>> verifySQLObject(IPOMessageID, RosettaPOMessageID)
    True
    '''

def test_verify_sql_potranslationsighting():
    '''
    >>> from canonical.rosetta.interfaces import IPOTranslationSighting
    >>> from canonical.rosetta.sql import RosettaPOTranslationSighting
    >>> verifySQLObject(IPOTranslationSighting, RosettaPOTranslationSighting)
    True
    '''

def test_verify_sql_potranslation():
    '''
    >>> from canonical.rosetta.interfaces import IPOTranslation
    >>> from canonical.rosetta.sql import RosettaPOTranslation
    >>> verifySQLObject(IPOTranslation, RosettaPOTranslation)
    True
    '''

def test_verify_sql_branch():
    '''
    >>> from canonical.rosetta.interfaces import IBranch
    >>> from canonical.rosetta.sql import RosettaBranch
    >>> verifySQLObject(IBranch, RosettaBranch)
    True
    '''

def test_verify_sql_person():
    '''
    >>> from canonical.rosetta.interfaces import IPerson
    >>> from canonical.rosetta.sql import RosettaPerson
    >>> verifySQLObject(IPerson, RosettaPerson)
    True
    '''

def test_verify_sql_language():
    '''
    >>> from canonical.rosetta.interfaces import ILanguage
    >>> from canonical.rosetta.sql import RosettaLanguage
    >>> verifySQLObject(ILanguage, RosettaLanguage)
    True
    '''

def test_verify_sql_languages():
    '''
    >>> from canonical.rosetta.interfaces import ILanguages
    >>> from canonical.rosetta.sql import RosettaLanguages
    >>> verifySQLObject(ILanguages, RosettaLanguages)
    True
    '''


def test_suite():
    suite = DocTestSuite()
    return suite

if __name__ == '__main__':
    r = unittest.TextTestRunner()
    r.run(DocTestSuite())

