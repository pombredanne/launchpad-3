# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# This is the canonical.foaf Python package.
#
# The FOAF (Friend of a Friend) subsystem of Launchpad tracks
# people that work on Open Source software.

__metaclass__ = type

from zope.interface import implements
from zope.app.container.interfaces import IContained

from canonical.launchpad.interfaces import IFOAFApplication
from canonical.publication import rootObject

# This is the core FOAF application that handles /foaf/
# URLs and gives us an anchor for further URL traversal and
# code.

class FOAFApplication(object):
    implements(IFOAFApplication, IContained)

    __parent__ = rootObject

