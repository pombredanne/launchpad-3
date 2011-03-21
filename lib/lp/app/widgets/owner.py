# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import getUtility
from zope.interface import implements, Interface
from zope.app.form.interfaces import IInputWidget
from zope.app.form.browser.interfaces import IBrowserWidget

from canonical.launchpad.webapp.interfaces import ILaunchBag

class RequestWidget(object):
    '''A widget that sets itself to a value calculated from request

    This is a bit of a hack, but necessary. If we are using the Zope
    form generation machinery, then the only things that know about request
    are the Views (the AddView and the Widgets). It is easier to define
    a custom widget than to override the AddView
    '''
    implements(IInputWidget, IBrowserWidget)

    _prefix = 'field.'
    name = ''
    hint = ''
    label = ''
    required = False
    visible = False

    def __init__(self, context, request):
        # We are a View
        self.context = context
        self.request = request
        self.name = self._prefix + context.__name__

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

    def setPrefix(self, prefix):
        '''See zope.app.form.interfaces.IWidget'''
        if not prefix.endswith("."):
            prefix += '.'
        self._prefix = prefix
        self.name = prefix + self.context.__name__

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


class IUserWidget(Interface):
    pass


class HiddenUserWidget(RequestWidget):
    implements(IUserWidget)
    def __init__(self, context, vocabulary, request=None):
        '''Construct the HiddenUserWidget.

        Zope 3.2 changed the signature of widget constructors used
        with Choice fields. This broke a number of our widgets, and
        causes problems for widgets like this one that were being used
        both in Choice fields and in other fields. This constructor
        has been modified to accept either the three or four arguments
        to allow it to keep working with all field types.
        '''
        if request is None:
            request = vocabulary
        RequestWidget.__init__(self, context, request)

    def getInputValue(self):
        return getUtility(ILaunchBag).user
