# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# This is the canonical.malone python package.

__metaclass__ = type

from zope.interface import implements
#from zope.app.form.browser.interfaces import IAddFormCustomization

from canonical.launchpad.interfaces import IMaloneApplication
from canonical.publication import rootObject

class MaloneApplication(object):
    implements(IMaloneApplication)

