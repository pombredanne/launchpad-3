# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# This is the canonical.doap Python package.
#
# The DOAP (Description Of A Project) subsystem of Launchpad
# tracks projects, products, product releases and series' of
# releases.
#

__metaclass__ = type

from zope.interface import implements
from zope.app.container.interfaces import IContained

from canonical.launchpad.interfaces import IDOAPApplication
from canonical.publication import rootObject

from canonical.doap.fileimporter import ProductReleaseImporter

#
# This is the core DOAP application, it's what handles /doap/
# URLs and gives us an anchor for further URL traversal and
# code.
#
class DOAPApplication(object):
    implements(IDOAPApplication, IContained)

    __parent__ = rootObject

    name = 'DOAP'
