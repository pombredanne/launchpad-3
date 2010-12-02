# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211

"""Single selection widget using a popup to select one item from many."""

__metaclass__ = type

import cgi
import os

import simplejson
from z3c.ptcompat import ViewPageTemplateFile
from zope.app.form.browser.itemswidgets import (
    ItemsWidgetBase,
    SingleDataHelper,
    )
from zope.schema.interfaces import IChoice

from canonical.launchpad.webapp import canonical_url
from lp.services.propertycache import cachedproperty


class VocabularyPickerWidget(SingleDataHelper, ItemsWidgetBase):
    """Wrapper for the lazr-js picker/picker.js widget."""

    __call__ = ViewPageTemplateFile('templates/form-picker.pt')

    popup_name = 'popup-vocabulary-picker'

    # Override inherited attributes for the form field.
    displayWidth = '20'
    displayMaxWidth = ''
    default = ''
    onKeyPress = ''
    style = ''
    cssClass = ''

    step_title = None
    # Defaults to self.vocabulary.displayname.
    header = None

    @cachedproperty
    def matches(self):
        """Return a list of matches (as ITokenizedTerm) to whatever the
        user currently has entered in the form.
        """
        # Pull form value using the parent class to avoid loop
        formValue = super(VocabularyPickerWidget, self)._getFormInput()
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
            'formToken': cgi.escape(self.formToken, quote=True),
            'name': self.name,
            'displayWidth': self.displayWidth,
            'displayMaxWidth': self.displayMaxWidth,
            'onKeyPress': self.onKeyPress,
            'style': self.style,
            'cssClass': self.cssClass,
            }
        return """<input type="text" value="%(formToken)s" id="%(name)s"
                         name="%(name)s" size="%(displayWidth)s"
                         maxlength="%(displayMaxWidth)s"
                         onKeyPress="%(onKeyPress)s" style="%(style)s"
                         class="%(cssClass)s" />""" % d

    @property
    def suffix(self):
        return self.name.replace('.', '-')

    @property
    def show_widget_id(self):
        return 'show-widget-%s' % self.suffix

    @property
    def extra_no_results_message(self):
        """Extra message when there are no results.

        Override this in subclasses.

        :return: A string that will be passed to Y.Node.create()
                 so it needs to be contained in a single HTML element.
        """
        return None

    @property
    def vocabulary_name(self):
        """The name of the field's vocabulary."""
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
        return choice.vocabularyName

    def js_template_args(self):
        """return a dict of args to configure the picker javascript."""
        if self.header is None:
            header = self.vocabulary.displayname
        else:
            header = self.header

        if self.step_title is None:
            step_title = self.vocabulary.step_title
        else:
            step_title = self.step_title

        return dict(
            vocabulary=self.vocabulary_name,
            header=header,
            step_title=step_title,
            show_widget_id=self.show_widget_id,
            input_id=self.name,
            extra_no_results_message=self.extra_no_results_message)

    def chooseLink(self):
        js_file = os.path.join(os.path.dirname(__file__),
                               'templates/vocabulary-picker.js.template')
        js_template = open(js_file).read()
        args = self.js_template_args()
        js = js_template % simplejson.dumps(args)
        # If the YUI widget or javascript is not supported in the browser,
        # it will degrade to being this "Find..." link instead of the
        # "Choose..." link. This only works if a non-AJAX form is available
        # for the field's vocabulary.
        if self.nonajax_uri is None:
            css = 'unseen'
        else:
            css = ''
        return ('<span class="%s">(<a id="%s" href="/people/">'
                'Find&hellip;</a>)</span>'
                '\n<script>\n%s\n</script>') % (css, self.show_widget_id, js)

    @property
    def nonajax_uri(self):
        """Override in subclass to specify a non-AJAX URI for the Find link.

        If None is returned, the find link will be hidden.
        """
        return None


class PersonPickerWidget(VocabularyPickerWidget):
    include_create_team_link = False

    def chooseLink(self):
        link = super(PersonPickerWidget, self).chooseLink()
        if self.include_create_team_link:
            link += ('or (<a href="/people/+newteam">'
                     'Create a new team&hellip;</a>)')
        return link

    @property
    def nonajax_uri(self):
        return '/people/'


class BugTrackerPickerWidget(VocabularyPickerWidget):
    link_template = """
        or (<a id="%(activator_id)s" href="/bugs/bugtrackers/+newbugtracker"
                    >Register an external bug tracker&hellip;</a>)
        <script>
        LPS.use('lp.bugs.bugtracker_overlay', function(Y) {
            if (Y.UA.ie) {
                return;
            }
            Y.on('domready', function () {
                // After the success handler finishes, it calls the
                // next_step function.
                var next_step = function(bug_tracker) {
                    // Fill in the text field with either the name of
                    // the newly created bug tracker or the name of an
                    // existing bug tracker whose base_url matches.
                    var bugtracker_text_box = Y.one(
                        Y.DOM.byId('field.bugtracker.bugtracker'));
                    if (bugtracker_text_box !== null) {
                        bugtracker_text_box.set(
                            'value', bug_tracker.get('name'));
                        // It doesn't appear possible to use onChange
                        // event, so the onKeyPress event is explicitely
                        // fired here.
                        if (bugtracker_text_box.get('onkeypress')) {
                            bugtracker_text_box.get('onkeypress')();
                        }
                        bugtracker_text_box.scrollIntoView();
                    }
                }
                Y.lp.bugs.bugtracker_overlay.attach_widget({
                    activate_node: Y.get('#%(activator_id)s'),
                    next_step: next_step
                    });
                });
        });
        </script>
        """

    def chooseLink(self):
        link = super(BugTrackerPickerWidget, self).chooseLink()
        link += self.link_template % dict(
            activator_id='create-bugtracker-link')
        return link

    @property
    def nonajax_uri(self):
        return '/bugs/bugtrackers/'


class SearchForUpstreamPopupWidget(VocabularyPickerWidget):
    """A SinglePopupWidget with a custom error message.

    This widget is used only when searching for an upstream that is also
    affected by a given bug as the page it links to includes a link which
    allows the user to register the upstream if it doesn't exist.
    """

    @property
    def extra_no_results_message(self):
        return ("<strong>Didn't find the project you were looking for? "
                '<a href="%s/+affects-new-product">Register it</a>.</strong>'
                % canonical_url(self.context.context))
