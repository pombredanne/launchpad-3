# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import sys
from types import ClassType
from zope.interface.advice import addClassAdvisor
from zope.interface import classImplements

from sqlobject import connectionForURI
from canonical.database.sqlbase import SQLBase

dbname = "launchpad_test"
dbhost = ""

def initZopeless():
    SQLBase.initZopeless(connectionForURI('postgres://%s/%s' %
        (dbhost, dbname)))

def decorates(interface, context='context'):
    """Make an adapter into a decorator.

    Use like:

      class RosettaProject:
          implements(IRosettaProject)
          decorates(IProject)

          def __init__(self, context):
              self.context = context

          def methodFromRosettaProject(self):
              return self.context.methodFromIProject()

    If you want to use a different name than "context" then you can explicitly
    say so:

      class RosettaProject:
          implements(IRosettaProject)
          decorates(IProject, context='project')

          def __init__(self, project):
              self.project = project

          def methodFromRosettaProject(self):
              return self.project.methodFromIProject()

    The adapter class will implement the interface it is decorating.

    The minimal decorator looks like this:

      class RosettaProject:
          decorates(IProject)

          def __init__(self, context):
              self.context = context

    """
    frame = sys._getframe(1)
    locals = frame.f_locals

    # Try to make sure we were called from a class def
    if (locals is frame.f_globals) or ('__module__' not in locals):
        raise TypeError("decorates can be used only from a class definition.")

    locals['__decorates_advice_data__'] = interface, context
    addClassAdvisor(_decorates_advice, depth=2)

def _decorates_advice(cls):
    interface, contextvar = cls.__dict__['__decorates_advice_data__']
    del cls.__decorates_advice_data__
    if type(cls) is ClassType:
        raise TypeError('cannot use decorates() on a classic class: %s' %
                        cls)
    classImplements(cls, interface)
    for name in interface:
        if not hasattr(cls, name):
            setattr(cls, name, Passthrough(name, contextvar))
    return cls

class Passthrough:

    def __init__(self, name, contextvar):
        self.name = name
        self.contextvar = contextvar

    def __get__(self, inst, cls=None):
        if inst is None:
            return self
        else:
            return getattr(getattr(inst, self.contextvar), self.name)

    def __set__(self, inst, value):
        setattr(getattr(inst, self.contextvar), self.name, value)

    def __delete__(self, inst):
        raise NotImplementedError

