# Zope
from zope.interface import implements
from zope.component import getUtility
from zope.exceptions import NotFoundError

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE, OR

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import DEFAULT

# LP Interfaces
from canonical.launchpad.interfaces import ICodeOfConduct, ICodeOfConductSet,\
                                           ICodeOfConductConf

from canonical.launchpad.interfaces import ISignedCodeOfConduct, \
                                           ISignedCodeOfConductSet

# Python
import os

class CodeOfConduct(object):
    """Code of Conduct"""

    implements(ICodeOfConduct)

    def __init__(self, version):        
        self.version = version


    def _getTitle(self):
        """Return Pre Formatted Title."""
        # Recover the prefix for CoC from a Component
        prefix = getUtility(ICodeOfConductConf).prefix

        # Build a fancy title
        return prefix + self.version 
        
    title = property(_getTitle)

    def _getContent(self):
        """Return the Content of the CoC file """
        # Recover the path for CoC from a Component
        path = getUtility(ICodeOfConductConf).path

        # Rebuild filename
        filename = os.path.join(path, self.version + '.txt')

        try:
            fp = open(filename)
            ## XXX: cprov 20050217
            ## Is there any ZopeComponent available
            ## to fancy present the file content (WikiFormat)?
            data = fp.read()
            fp.close()
        except IOError:
            raise NotFoundError('CoC Release Not Found')
        
        return data

    content = property(_getContent)

    def _isCurrent(self):
        """Return True if it is the Current Release."""

        if getUtility(ICodeOfConductConf).current == self.version :
            return True
        
        return False
    
    current = property(_isCurrent)

class CodeOfConductSet(object):
    """A set of CodeOfConducts"""

    implements(ICodeOfConductSet)

    def __getitem__(self, version):
        """Get a Pristine CoC Release."""
        return CodeOfConduct(version)
        
    def __iter__(self):
        """Iterate through the Pristine CoC release in this set."""

        releases = []
        
        # Recover the path for CoC from a Component
        cocs_path = getUtility(ICodeOfConductConf).path

        # iter through files and store the the CoC Object
        for filename in os.listdir(cocs_path):

            # Select the Correct filenames
            if filename.endswith('.txt'):
                
                # Extract the version from filename
                version = filename.replace('.txt', '')
                
                releases.append(CodeOfConduct(version))

        # Return the available list of CoCs objects
        return iter(releases)

class CodeOfConductConf(object):
    """Abstract Component to store the current CoC Conf."""

    implements(ICodeOfConductConf)

    ## XXX: cprov 20050217
    ## Integrate it with LP Central conf in the future

    path = 'lib/canonical/launchpad/templates/codesofconduct/'
    prefix = 'Ubuntu Code of Conduct - '
    current = '1.0'

