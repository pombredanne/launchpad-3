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
    formToken = Attribute(
            'fromToken',
            'The token representing the value to display, possilby invalid'
            )
    popupHref = Attribute(
            'popupHref',
            '''The contents to go into the href tag used to popup 
               the select window'''
            )

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

    def _getFormValue(self):
        rv = super(SinglePopupWidget, self)._getFormValue()
        logging.warn('SinglePopupWidget._getFormValue() == %r' % (rv,))
        return rv

    def _getFormToken(self):
        val = self._getFormValue()
        if isinstance(val, basestring):
            return val
        else:
            return self.vocabulary.getTerm(val).token

    def _getPopupHref(self):
        template = (
            '''javascript:'''
            '''popup_window('@@popup-window?'''
            '''vocabulary=%s&field=%s','''
            ''''500','400')'''
            )
        return template % (self.context.vocabularyName, self.name)
            

    formToken = property(_getFormToken)
    popupHref = property(_getPopupHref)


class ISinglePopupView(Interface):

    def title():
        'Title to use on the popup page'

    def vocabulary():
        'Return the IHugeVocabulary to display in the popup window'

    def batch():
        'Return the BatchNavigator of the current results to display'

class SinglePopupView(object):
    implements(ISinglePopupView)

    batchsize = 2

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

