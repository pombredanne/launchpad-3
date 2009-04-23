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

from zope.security.checker import canWrite
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from canonical.launchpad.webapp.publisher import canonical_url


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

    __call__ = ViewPageTemplateFile('templates/inline-picker.pt')

    def __init__(self, context, request, py_attribute, json_attribute,
                 json_attribute_uri_base,
                 vocabulary, default_html, id=None,
                 header='Select an item', step_title='Search',
                 show_remove_button=False, show_assign_me_button=False,
                 remove_button_text=None):
        """Create a widget wrapper.

        :param context: The object that is being edited.
        :param request: Request object.
        :param py_attribute: The name of the attribute being edited in python.
        :param json_attribute: The name of the attribute in json. Sometimes
                               "_link" is added to the attribute name. For
                               example, "assignee" becomes "assignee_link".
        :param json_attribute_uri_base: For example, 'person' needs to be
                                        '/~person', so the base is '/~'.
        :param vocabulary: The vocabulary that the picker will search.
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
        self.py_attribute = py_attribute
        self.json_attribute = json_attribute
        self.json_attribute_uri_base = json_attribute_uri_base
        self.vocabulary = vocabulary
        self.default_html = default_html
        self.header = header
        self.step_title = step_title
        self.show_remove_button = simplejson.dumps(show_remove_button)
        self.show_assign_me_button = simplejson.dumps(show_assign_me_button)
        self.remove_button_text = remove_button_text

        if id is None:
            self.id = self._generate_id()
        else:
            self.id = id

    @classmethod
    def delete_button_id(self):
        return 'delete-button-%s' % self.id

    @classmethod
    def _generate_id(cls):
        """Return a presumably unique id for this widget."""
        cls.last_id += 1
        return 'inline-picker-activator-id-%d' % cls.last_id

    @property
    def config(self):
        return simplejson.dumps(
            dict(header=self.header, step_title=self.step_title,
                 remove_button_text=self.remove_button_text))

    @property
    def resource_uri(self):
        return canonical_url(self.context, path_only_if_possible=True)
