""" A module for CodeOfConduct (CoC) related classes.
    
    https://wiki.launchpad.canonical.com/CodeOfConduct
    
    Copyright 2004 Canonical Ltd.  All rights reserved.
"""

__metaclass__ = type

# Zope
from zope.interface import implements
from zope.component import getUtility
from zope.exceptions import NotFoundError

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.database.sqlbase import SQLBase, quote
from canonical.database.constants import DEFAULT

# LP Interfaces
from canonical.launchpad.interfaces import ICodeOfConduct, ICodeOfConductSet,\
                                           ICodeOfConductConf

from canonical.launchpad.interfaces import ISignedCodeOfConduct, \
                                           ISignedCodeOfConductSet

# Python
import os
from datetime import datetime

class CodeOfConduct(object):
    """CoC class model.
    A set of properties allow us to properly handle the CoC stored
    in the filesystem, so it's not a database class.
    """
    
    implements(ICodeOfConduct)

    def __init__(self, version):        
        self.version = version

    def _getTitle(self):
        """Return preformatted title (config_prefix + version)."""

        ## XXX: cprov 20050218
        ## Missed doctest, problems initing ZopeComponentLookupError
        
        # Recover the prefix for CoC from a Component
        prefix = getUtility(ICodeOfConductConf).prefix

        # Build a fancy title
        return prefix + self.version 
        
    title = property(_getTitle)

    def _getContent(self):
        """Return the content of the CoC file."""
        # Recover the path for CoC from a Component
        path = getUtility(ICodeOfConductConf).path

        # Rebuild filename
        filename = os.path.join(path, self.version + '.txt')

        try:
            fp = open(filename)
        except IOError, e:
            if e.errno == errno.EEXIST:
                # File not found means the requested CoC was not found.
                raise NotFoundError('CoC Release Not Found')

            # All other IOErrors are a problem, though.
            raise
        else:
            data = fp.read()
            fp.close()
        
        return data

    content = property(_getContent)

    def _isCurrent(self):
        """Is this the current release of the Code of Conduct?"""
        return getUtility(ICodeOfConductConf).current == self.version
    
    current = property(_isCurrent)


class CodeOfConductSet(object):
    """A set of CodeOfConducts"""

    implements(ICodeOfConductSet)

    def __getitem__(self, version):
        """See ICodeOfConductSet."""
        # Create an entry point for the Admin Console
        # Obviously we are excluding a CoC version called 'admin'
        if version == 'admin':
            return SignedCodeOfConductSet()
        # in normal conditions return the CoC Release
        return CodeOfConduct(version)
        
    def __iter__(self):
        """See ICodeOfConductSet."""
        releases = []
        
        # Recover the path for CoC from a component
        cocs_path = getUtility(ICodeOfConductConf).path

        # iter through files and store the the CoC Object
        for filename in os.listdir(cocs_path):

            # Select the correct filenames
            if filename.endswith('.txt'):
                
                # Extract the version from filename
                version = filename.replace('.txt', '')
                
                releases.append(CodeOfConduct(version))

        # Return the available list of CoCs objects
        return iter(releases)


class CodeOfConductConf(object):
    """Abstract Component to store the current CoC configuration."""

    implements(ICodeOfConductConf)

    ## XXX: cprov 20050217
    ## Integrate this class with LaunchpadCentral configuration
    ## in the future

    path = 'lib/canonical/launchpad/templates/codesofconduct/'
    prefix = 'Ubuntu Code of Conduct - '
    current = '1.0'



class SignedCodeOfConduct(SQLBase):
    """Code of Conduct"""

    implements(ISignedCodeOfConduct)

    _table = 'SignedCodeOfConduct'

    person = ForeignKey(foreignKey="Person", dbName="person",
                        notNull=True)
    
    signedcode = StringCol(dbName='signedcode', notNull=False, default=None)

    signingkey = StringCol(dbName='signingkey', notNull=False, default=None)

    datecreated = DateTimeCol(dbName='datecreated', notNull=False,
                              default=datetime.utcnow())

    recipient = ForeignKey(foreignKey="Person", dbName="recipient",
                           notNull=False, default=None)
    
    admincomment = StringCol(dbName='admincomment', notNull=False,
                             default=None)
    
    active = BoolCol(dbName='active', notNull=False, default=False)
    

    def _getDisplayName(self):
        """Build a Fancy Title for CoC."""
        # XXX: cprov 20040224
        # We need the proposed field 'version'
        return '%s (%s)' % (self.person.displayname, self.signingkey)

    displayname = property(_getDisplayName)

class SignedCodeOfConductSet(object):
    """A set of CodeOfConducts"""

    implements(ISignedCodeOfConductSet)

    def __getitem__(self, id):
        """Get a Signed CoC Entry."""
        return SignedCodeOfConduct.get(id)


    def __iter__(self):
        """Iterate through the Signed CoC."""
        return iter(SignedCodeOfConduct.select())


    def verifyAndStore(self, person, signingkey, signedcode):
        """See ISignedCodeOfConductSet"""
        # XXX cprov 20050224
        # Are we missing the version field in SignedCoC table ?
        # how to figure out how CoC version is signed ?
        SignedCodeOfConduct(person=person, signingkey=signingkey,
                            signedcode=signedcode)

    def searchByDisplayname(self, displayname, searchfor=None):
        """See ISignedCodeOfConductSet"""
        displayname = displayname.replace('%', '%%')

        clauseTables = ['Person',]
        
        # use FTI
        query = ('SignedCodeOfConduct.person = Person.id AND '
                 'Person.fti @@ ftq(%s)'
                 % quote(displayname))

        if searchfor == 'activeonly':
            query += ' AND SignedCodeOfConduct.active = true'
            
        elif searchfor == 'inactiveonly':
            query += ' AND SignedCodeOfConduct.active = false'
        
        return SignedCodeOfConduct.select(query, clauseTables=clauseTables)
