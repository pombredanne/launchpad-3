from zope.interface import Attribute, implements, Interface
from zope.app import zapi
from zope.app.form.browser.interfaces import ISimpleInputWidget
from zope.app.form.browser.itemswidgets import ItemsWidgetBase, SingleDataHelper
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.schema.vocabulary import IVocabularyFactory

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.launchpad.vocabularies import IHugeVocabulary

import logging

from canonical.lp import _

class ISinglePopupWidget(ISimpleInputWidget):
    def formToken():
        'The token representing the value to display, possibly invalid'
    def popupHref():
        'The contents to go into the href tag used to popup the select window'
    def matches():
        'List of tokens matching the current input'


class SinglePopupWidget(SingleDataHelper, ItemsWidgetBase):
    """Window popup widget for single item choices from a huge vocabulary.

    The huge vocabulary must be registered by name in the vocabulary registry.

    """
    implements(ISinglePopupWidget)

    # ZPT that renders our widget

    __call__ = ViewPageTemplateFile('templates/popup.pt')

    default = ''
    displayWidth = 20
    displayMaxWidth = None
    style = None

    def _old_getFormValue(self):
        # Check to see if there is only one possible match. If so, use it.
        matches = self.matches()
        if len(matches) == 1:
            return matches[0].token

        # Otherwise, return the invalid value the user entered
        return super(SinglePopupWidget, self)._getFormValue()
        return rv

    def _getFormInput(self):
        '''See zope.app.form.browser.widget.SimpleWidget'''
        matches = self.matches()
        if len(matches) == 1:
            return matches[0].token
        else:
            return super(SinglePopupWidget, self)._getFormInput()

    _matches = None
    def matches(self):
        '''Return a list of matches (as ITokenizedTerm) to whatever the
           user currently has entered in the form. 

        '''
        # Use a cached version if we have it to avoid repeating expensive
        # searches
        if self._matches is not None:
            return self._matches

        # Pull form value using the parent class to avoid loop
        formValue = super(SinglePopupWidget, self)._getFormInput()
        if not formValue:
            return []

        # Special case - if the entered value is valid, it is an object
        # rather than a string (I think this is a bug somewhere)
        if not isinstance(formValue, basestring):
            self._matches = [self.vocabulary.getTerm(formValue)]
            return self._matches

        # Cache and return the search
        self._matches = list(self.vocabulary.search(formValue))
        return self._matches
        
    def formToken(self):
        val = self._getFormValue()

        # We have a valid object - return the corresponding token
        if not isinstance(val, basestring):
            return self.vocabulary.getTerm(val).token

        # Just return the existing invalid token
        return val

    def popupHref(self):
        template = (
            '''javascript:'''
            '''popup_window('@@popup-window?'''
            '''vocabulary=%s&field=%s','''
            ''''500','400')'''
            )
        return template % (self.context.vocabularyName, self.name)
            

class ISinglePopupView(Interface):

    def title():
        'Title to use on the popup page'

    def vocabulary():
        'Return the IHugeVocabulary to display in the popup window'

    def batch():
        'Return the BatchNavigator of the current results to display'

class SinglePopupView(object):
    implements(ISinglePopupView)

    batchsize = 15

    def title(self):
        return _(u'Select %s' % self.request.form['vocabulary'])

    def vocabulary(self):
        factory = zapi.getUtility(IVocabularyFactory,
            self.request.form['vocabulary']
            )
        vocabulary = factory(self.context)
        assert IHugeVocabulary.providedBy(vocabulary), \
                'Invalid vocabulary %s' % self.request.form['vocabulary']
        return vocabulary

    def batch(self):
        # TODO: Dead chickens here! batching module needs refactoring.
        # batch_end seems pointless too
        # StuartBishop 2004/11/12
        start = int(self.request.get('batch_start', 0))
        #end = int(self.request.get('batch_end', self.batchsize))
        search = self.request.get('search', None)
        batch = Batch(
                list=list(self.vocabulary().search(search)),
                start=start, size=self.batchsize
                )
        return BatchNavigator(batch=batch, request=self.request)

