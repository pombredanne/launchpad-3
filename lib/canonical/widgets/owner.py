# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 7ab5b92b-af62-4e4e-aff9-bd9f4279d915

__metaclass__ = type

from zope.interface import implements, Interface
from zope.app.form.interfaces import IInputWidget
from zope.app.form.browser.interfaces import IBrowserWidget
from canonical.launchpad.interfaces import IPerson

class RequestWidget(object):
    '''A widget that sets itself to a value calculated from request

    This is a bit of a hack, but necessary. If we are using the Zope
    form generation machinery, then the only things that know about request
    are the Views (the AddView and the Widgets). It is easier to define
    a custom widget than to override the AddView
    '''
    implements(IInputWidget, IBrowserWidget)

    name = ''
    hint = ''
    label = ''

    def __init__(self, context, request):
        # We are a View
        self.context = context
        self.request = request

    def validate(self):
        '''See zope.app.form.interfaces.IInputWidget'''
        return self.getValueFromRequest(self.request)

    def getInputValue(self):
        '''See zope.app.form.interfaces.IInpputWidget'''
        raise NotImplementedError, 'getInputValue'

    def applyChanges(self, content):
        '''See zope.app.form.interfaces.IInputWidget'''
        field = self.context
        value = self.getInputValue(self.request)
        if field.query(content, self) != value:
            field.set(content, value)
            return True
        else:
            return False

    def hasInput(self):
        '''See zope.app.form.interfaces.IInputWidget'''
        return True

    def __call__(self):
        '''See zope.app.form.browser.interfaces.IBrowserWidget'''
        return ''

    def hidden(self):
        '''See zope.app.form.browser.interfaces.IBrowserWidget'''
        return ''

    def error(self):
        '''See zope.app.form.browser.interfaces.IBrowserWidget'''
        return ''

class IOwnerWidget(Interface):
    pass

class OwnerWidget(RequestWidget):
    implements(IOwnerWidget)
    def getInputValue(self):
        return IPerson(self.request.principal)


