"""General App Componentes for Soyuz.

(c) Canonical Software Ltd. 2004, all rights reserved.
"""

# Python standard library imports
from string import strip

# Zope imports
from zope.interface import implements


#
# 
#

class builddepsContainer(object):
    def __init__(self, name, version, signal):
        self.name = name
        self.version = version
        if len(strip(signal)) == 0:
            signal = None
        self.signal = signal

    
class CurrentVersion(object):
    def __init__(self, release, builds):
        self.release = release
        self.currentversion = release.version
        self.currentbuilds = builds

