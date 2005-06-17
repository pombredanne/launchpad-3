# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""
Create a .zcml snippet that processes the current config's ZCML overrides.

This avoids us having to hook into the Z3 internals to get the files processed
at the right time.
"""

__metaclass__ = type

import os, os.path

def generate_overrides():
    """Ensure correct config .zcml overrides will be called.
    
    Call this method before letting any ZCML processing occur.
    """

    mydir = os.path.dirname(__file__)
    config = os.environ.get('LPCONFIG', 'default')

    loader_file = os.path.join(mydir, '+config-overrides.zcml')
    loader = open(loader_file, 'w')

    print >> loader, """<configure xmlns="http://namespaces.zope.org/zope">
            <!-- This file automatically generated using
                 configs.generate_overrides. DO NOT EDIT. -->
            <include files="%(config)s/*.zcml" />
            </configure>""" % vars()
    loader.close()

if __name__=="__main__":
    generate_overrides()

