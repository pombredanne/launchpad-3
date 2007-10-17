#!/usr/bin/python2.4
"""Copyright Canonical Limited 2005
 Author: Daniel Silverstone <daniel.silverstone@canonical.com>
         Celso Providelo <celso.providelo@canonical.com>
 Simple tool to upload arbitrary files into Librarian
"""
from canonical.lp import initZopeless
from canonical.launchpad.scripts import execute_zcml_for_scripts
from zope.component import getUtility

from canonical.librarian.interfaces import ILibrarianClient
from canonical.launchpad.helpers import filenameToContentType

from optparse import OptionParser

import os

def addfile(filepath, client):
    """Add a file to librarian."""        
    # verify filepath
    if not filepath:
        print 'Filepath is required'
        return

    # open given file
    try:
        file = open(filepath)
    except IOError:
        print 'Could not open:', filepath
        return

    flen = os.stat(filepath).st_size
    filename = os.path.basename(filepath)
    ftype = filenameToContentType(filename)

    alias = client.addFile(filename, flen, file, contentType=ftype)

    print 'Added as', alias

    # commit previous transactions
    tm.commit()

if __name__ == '__main__':
    # Parse the commandline...
    parser = OptionParser()
    parser.add_option("-f","--file", dest="filepath",
                      help="filename to import",
                      metavar="FILE",
                      default=None)
    
    (options,args) = parser.parse_args()
    
    filepath = options.filepath

    # setup a transaction manager to LPDB
    tm = initZopeless()

    # load the zcml configuration
    execute_zcml_for_scripts()
    
    # get an librarian client instance
    client = getUtility(ILibrarianClient)

    addfile(filepath, client)
