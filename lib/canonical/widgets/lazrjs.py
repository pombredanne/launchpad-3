# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Wrappers for lazr-js widgets."""

__metaclass__ = type
__all__ = [
    'InlineEditPickerWidget',
    'TextLineEditorWidget',
    ]

import cgi
import simplejson
from textwrap import dedent

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.security.checker import canAccess, canWrite
from zope.schema.vocabulary import getVocabularyRegistry

from lazr.restful.interfaces import IWebServiceClientRequest

from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.vocabulary import IHugeVocabulary


class TextLineEditorWidget:
    """Wrapper for the lazr-js inlineedit/editor.js widget."""

    # Class variable used to generate a unique per-page id for the widget
    # in case it's not provided.
    last_id = 0


    # The HTML template used to render the widget.
    # Replacements:
    #   activation_script: the JS script to active the widget
    #   attribute: the name of the being edited
    #   context_url: the url to the current context
    #   edit_url: the URL used to edit the value when JS is turned off
    #   id: the widget unique id
    #   title: the widget title
    #   trigger: the trigger (button) HTML code
    #   value: the current field value
    WIDGET_TEMPLATE = dedent(u"""\
        <h1 id="%(id)s"><span
            class="yui-editable_text-text">%(value)s</span>
            %(trigger)s
        </h1>
        %(activation_script)s
        """)

    # Template for the trigger button.
    TRIGGER_TEMPLATE = dedent(u"""\
        <a href="%(edit_url)s" class="yui-editable_text-trigger"
        ><img src="/@@/edit" alt="[edit]" title="%(title)s" /></a>
        """)

    # Template for the activation script.
    ACTIVATION_TEMPLATE = dedent(u"""\
        <script>
        YUI().use('lazr.editor', 'lp.client.plugins', function (Y) {
            var widget = new Y.EditableText({
                contentBox: '#%(id)s',
            });
            widget.editor.plug({
                fn: Y.lp.client.plugins.PATCHPlugin, cfg: {
                  patch: '%(attribute)s',
                  resource: '%(context_url)s'}});
            widget.render();
        });
        </script>
        """)


    def __init__(self, context, attribute, edit_url, id=None, title="Edit"):
        """Create a widget wrapper.

        :param context: The object that is being edited.
        :param attribute: The name of the attribute being edited.
        :param edit_url: The URL to use for editing when the user isn't logged
            in and when JS is off.
        :param id: The HTML id to use for this widget. Automatically
            generated if this is not provided.
        :param title: The string to use as the link title. Defaults to 'Edit'.
        """
        self.context = context
        self.attribute = attribute
        self.edit_url = edit_url
        if id is None:
            self.id = self._generate_id()
        else:
            self.id = id
        self.title = title

    @classmethod
    def _generate_id(cls):
        """Return a presumably unique id for this widget."""
        cls.last_id += 1
        return 'inline-textline-editor-id%d' % cls.last_id

    def __call__(self):
        """Return the HTML to include to render the widget."""
        params = {
            'activation_script': '',
            'trigger': '',
            'edit_url': self.edit_url,
            'id': self.id,
            'title': self.title,
            'value': cgi.escape(getattr(self.context, self.attribute)),
            'context_url': canonical_url(
                self.context, path_only_if_possible=True),
            'attribute': self.attribute,
            }
        # Only display the trigger link and the activation script if
        # the user can write the attribute.
        if canWrite(self.context, self.attribute):
            params['trigger'] = self.TRIGGER_TEMPLATE % params
            params['activation_script'] = self.ACTIVATION_TEMPLATE % params
        return self.WIDGET_TEMPLATE % params


class InlineEditPickerWidget:
    """Wrapper for the lazr-js picker widget.

    This widget is not for editing form values like the
    VocabularyPickerWidget.
    """

    last_id = 0
    __call__ = ViewPageTemplateFile('templates/inline-picker.pt')

    def __init__(self, context, request, interface_attribute, default_html,
                 id=None, header='Select an item', step_title='Search',
                 remove_button_text='Remove', null_display_value='None'):
        """Create a widget wrapper.

        :param context: The object that is being edited.
        :param request: The request object.
        :param interface_attribute: The attribute being edited.
        :param default_html: Default display of attribute.
        :param id: The HTML id to use for this widget. Automatically
            generated if this is not provided.
        :param header: The large text at the top of the picker.
        :param step_title: Smaller line of text below the header.
        :param show_remove_button: Show remove button below search box.
        :param show_assign_me_button: Show assign-me button below search box.
        :param remove_button_text: Override default button text: "Remove"


        """
        self.context = context
        self.request = request
        self.default_html = default_html
        self.interface_attribute = interface_attribute
        self.attribute_name = interface_attribute.__name__

        if id is None:
            self.id = self._generate_id()
        else:
            self.id = id

        # JSON encoded attributes.
        self.json_id = simplejson.dumps(self.id)
        self.json_attribute = simplejson.dumps(self.attribute_name + '_link')
        self.vocabulary_name = simplejson.dumps(
            self.interface_attribute.vocabularyName)
        self.show_remove_button = simplejson.dumps(
            not self.interface_attribute.required)

        self.config = simplejson.dumps(
            dict(header=header, step_title=step_title,
                 remove_button_text=remove_button_text,
                 null_display_value=null_display_value))

    @property
    def show_assign_me_button(self):
        # show_assign_me_button is true if user is in the vocabulary.
        registry = getVocabularyRegistry()
        vocabulary = registry.get(
            IHugeVocabulary, self.interface_attribute.vocabularyName)
        user = getUtility(ILaunchBag).user
        return simplejson.dumps(user and user in vocabulary)

    @classmethod
    def _generate_id(cls):
        """Return a presumably unique id for this widget."""
        cls.last_id += 1
        return 'inline-picker-activator-id-%d' % cls.last_id

    @property
    def resource_uri(self):
        return simplejson.dumps(
            canonical_url(
                self.context, request=IWebServiceClientRequest(self.request),
                path_only_if_possible=True))

    @property
    def can_write(self):
        if canWrite(self.context, self.attribute_name):
            return True
        else:
            # The user may not have write access on the attribute itself, but
            # the REST API may have a mutator method configured, such as
            # transitionToAssignee.
            exported_tag = self.interface_attribute.getTaggedValue(
                'lazr.restful.exported')
            mutator = exported_tag.get('mutated_by')
            if mutator is not None:
                return canAccess(self.context, mutator.__name__)
            else:
                return False
