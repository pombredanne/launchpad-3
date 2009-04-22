# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Wrappers for lazr-js widgets."""

__metaclass__ = type
__all__ = [
    'vocabulary_to_choice_edit_items',
    'TextLineEditorWidget',
    ]

import cgi
from simplejson import dumps
from textwrap import dedent

from zope.security.checker import canWrite

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


def vocabulary_to_choice_edit_items(vocab):
    """ TODO """ # TODO
    items = [
        {'name': item.value.title,
         'value': item.value.title,
         'style': '', 'help': '', 'disabled': False}
        for item in vocab]
    return dumps(items)

