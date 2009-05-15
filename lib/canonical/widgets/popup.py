# Copyright 2006-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211

"""Single selection widget using a popup to select one item from many."""

__metaclass__ = type

import os
import cgi
import simplejson

from zope.interface import Attribute, implements, Interface
from zope.app import zapi
from zope.schema import TextLine
from zope.schema.interfaces import IChoice
from zope.app.form.browser.interfaces import ISimpleInputWidget
from zope.app.form.browser.itemswidgets import (
    ItemsWidgetBase, SingleDataHelper)
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.schema.vocabulary import IVocabularyFactory
from zope.publisher.interfaces import NotFound
from zope.component.interfaces import ComponentLookupError

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.vocabulary import IHugeVocabulary
from canonical.launchpad.interfaces import UnexpectedFormData
from canonical.cachedproperty import cachedproperty


class ISinglePopupWidget(ISimpleInputWidget):
    # I chose to use onKeyPress because onChange only fires when focus
    # leaves the element, and that's very inconvenient.
    onKeyPress = Attribute('''Optional javascript code to be executed
                              as text in input is changed''')
    cssClass = Attribute('''CSS class to be assigned to the input widget''')
    style = Attribute('''CSS style to be applied to the input widget''')
    popup_name = TextLine(
        title=u'The name our popup page is registered with.')
    def formToken():
        'The token representing the value to display, possibly invalid'
    def chooseLink():
        'The HTML link text and inline frame for the Choose.. link.'
    def inputField():
        'The HTML for the form input that is linked to this popup'
    def popupHref():
        'The contents to go into the href tag used to popup the select window'
    def matches():
        """List of tokens matching the current input.

        An empty list should be returned if 'too many' results are found.
        """


class SinglePopupWidget(SingleDataHelper, ItemsWidgetBase):
    """Window popup widget for single item choices from a huge vocabulary.

    The huge vocabulary must be registered by name in the vocabulary registry.
    """
    implements(ISinglePopupWidget)

    # ZPT that renders our widget

    __call__ = ViewPageTemplateFile('templates/popup.pt')

    default = ''

    displayWidth = '20'
    displayMaxWidth = ''
    onKeyPress = ''
    style = ''
    cssClass = ''
    popup_name = 'popup-window'

    @cachedproperty
    def matches(self):
        """Return a list of matches (as ITokenizedTerm) to whatever the
        user currently has entered in the form.
        """
        # Pull form value using the parent class to avoid loop
        formValue = super(SinglePopupWidget, self)._getFormInput()
        if not formValue:
            return []

        vocab = self.vocabulary
        # Special case - if the entered value is valid, it is an object
        # rather than a string (I think this is a bug somewhere)
        if not isinstance(formValue, basestring):
            return [vocab.getTerm(formValue)]

        search_results = vocab.searchForTerms(formValue)

        if search_results.count() > 25:
            # If we have too many results to be useful in a list, return
            # an empty list.
            return []

        return search_results

    @cachedproperty
    def formToken(self):
        val = self._getFormValue()

        # We have a valid object - return the corresponding token
        if not isinstance(val, basestring):
            return self.vocabulary.getTerm(val).token

        # Just return the existing invalid token
        return val

    def inputField(self):
        d = {
            'formToken' : cgi.escape(self.formToken, quote=True),
            'name': self.name,
            'displayWidth': self.displayWidth,
            'displayMaxWidth': self.displayMaxWidth,
            'onKeyPress': self.onKeyPress,
            'style': self.style,
            'cssClass': self.cssClass
        }
        return """<input type="text" value="%(formToken)s" id="%(name)s"
                         name="%(name)s" size="%(displayWidth)s"
                         maxlength="%(displayMaxWidth)s"
                         onKeyPress="%(onKeyPress)s" style="%(style)s"
                         class="%(cssClass)s" />""" % d

    def chooseLink(self):
        return """(<a href="%s" class="js-action">Choose&hellip;</a>)

            <iframe style="display: none"
                    id="popup_iframe_%s"
                    src="javascript:void(0);"
                    name="popup_iframe_%s"></iframe>
        """ % (self.popupHref(), self.name, self.name)

    def popupHref(self):
        template = (
            "javascript:"
            "popup_window('@@%s?"
            "vocabulary=%s&field=%s&search="
            "'+escape(document.getElementById('%s').value),"
            "'%s','300','420')"
            ) % (self.popup_name, self.context.vocabularyName, self.name,
                 self.name, self.name)
        if self.onKeyPress:
            # XXX kiko 2005-09-27: I suspect onkeypress() here is
            # non-standard, but it works for me, and enough researching for
            # tonight. It may be better to use dispatchEvent or a
            # compatibility function
            template += ("; document.getElementById('%s').onkeypress()" %
                         self.name)
        return template


class ISinglePopupView(Interface):

    batch = Attribute('The BatchNavigator of the current results to display')
    page_name = TextLine(title=u'The name this page is registered with.')

    def title():
        """Title to use on the popup page"""

    def vocabulary():
        """Return the IHugeVocabulary to display in the popup window."""

    def search():
        """Return the BatchNavigator of the current terms to display."""

    def hasMoreThanOnePage(self):
        """Return True if there's more than one page with results."""

    field = Attribute("The field parameter, sanitized.")


class SinglePopupView(object):
    implements(ISinglePopupView)

    _batchsize = 10
    batch = None
    page_name = 'popup-window'

    def __init__(self, context, request):
        if ("vocabulary" not in request.form or
            "field" not in request.form):
            # Hand-hacked URLs get no love from us
            raise NotFound(self, "/@@popup-window", request)
        self.context = context
        self.request = request

    def title(self):
        """See ISinglePopupView"""
        return self.vocabulary().displayname

    def vocabulary(self):
        """See ISinglePopupView"""
        vocabulary_name = self.request.form_ng.getOne('vocabulary')
        if not vocabulary_name:
            raise UnexpectedFormData('No vocabulary specified')
        try:
            factory = zapi.getUtility(IVocabularyFactory, vocabulary_name)
        except ComponentLookupError:
            # Couldn't find the vocabulary? Adios!
            raise UnexpectedFormData(
                'Unknown vocabulary %s' % vocabulary_name)

        vocabulary = factory(self.context)

        if not IHugeVocabulary.providedBy(vocabulary):
            raise UnexpectedFormData(
                'Non-huge vocabulary %s' % vocabulary_name)

        return vocabulary

    def search(self):
        """See ISinglePopupView"""
        search_text = self.request.get('search', None)
        self.batch = BatchNavigator(
            self.vocabulary().searchForTerms(search_text), self.request,
            size=self._batchsize)
        return self.batch

    def hasMoreThanOnePage(self):
        """See ISinglePopupView"""
        return len(self.batch.batchPageURLs()) > 1

    @property
    def field(self):
        """See ISinglePopupView"""
        return simplejson.dumps(self.request.form.get('field', None))


class SearchForUpstreamPopupWidget(SinglePopupWidget):
    """A SinglePopupWidget whose 'Choose' link opens a different page.

    This widget is used only when searching for an upstream that is also
    affected by a given bug as the page it links to includes a link which
    allows the user to register the upstream if it doesn't exist.
    """
    popup_name = 'popup-search-upstream'


class SearchForUpstreamPopupView(SinglePopupView):

    page_name = 'popup-search-upstream'

    @property
    def extra_bottom(self):
        search_text = self.request.get('search')
        if not search_text:
            return ''
        return ("Didn't find the project you were looking for? "
                '<a href="%s/+affects-new-product" target="_parent">'
                'Register it</a>.' % canonical_url(self.context))


class VocabularyPickerWidget(SinglePopupWidget):
    """Wrapper for the lazr-js picker/picker.js widget."""

    popup_name = 'popup-vocabulary-picker'

    header = 'Select an item'

    step_title = 'Search'

    @property
    def suffix(self):
        return self.name.replace('.', '-')

    @property
    def show_widget_id(self):
        return 'show-widget-%s' % self.suffix

    def chooseLink(self):
        js_file = os.path.join(os.path.dirname(__file__),
                               'templates/vocabulary-picker.js')
        js_template = open(js_file).read()

        choice = IChoice(self.context)
        if choice.vocabularyName is None:
            # The webservice that provides the results of the search
            # must be passed in the name of the vocabulary which is looked
            # up by the vocabulary registry.
            raise ValueError(
                "The %r.%s interface attribute doesn't have its "
                "vocabulary specified as a string, so it can't be loaded "
                "by the vocabulary registry."
                % (choice.context, choice.__name__))
        js = js_template % dict(
            vocabulary=choice.vocabularyName,
            header=self.header,
            step_title=self.step_title,
            show_widget_id=self.show_widget_id,
            input_id=self.name)
        # If the YUI widget or javascript is not supported in the browser,
        # it will degrade to being this "Find..." link instead of the
        # "Choose..." link.
        return ('(<a id="%s" href="/people/">'
                'Find&hellip;</a>)'
                '\n<script>\n%s\n</script>') % (self.show_widget_id, js)


class PersonPickerWidget(VocabularyPickerWidget):
    header = 'Select a person or team'
    include_create_team_link = False

    def chooseLink(self):
        link = super(PersonPickerWidget, self).chooseLink()
        if self.include_create_team_link:
            link += ('or (<a href="/people/+newteam">'
                     'Create a new team&hellip;</a>)')
        return link
