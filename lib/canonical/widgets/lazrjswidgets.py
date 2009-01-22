# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Wrappers for lazr-js widgets."""

__metaclass__ = type
__all__ = [
    'InlineTextLineEditorWidget',
    ]

import cgi
from textwrap import dedent

from zope.component import getUtility
from zope.security.checker import canWrite

from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.publisher import canonical_url


class InlineTextLineEditorWidget:
    """Wrapper for the lazr-js inlineedit/editor.js widget."""

    last_id = 0

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
            params['trigger'] = dedent(u"""\
                <a href="%(edit_url)s" class="yui-editable_text-trigger"
                ><img src="/@@/edit" alt="[edit]" title="%(title)s" /></a>
                """ % params)
            params['activation_script'] = dedent(u"""\
                <script>
                YUI().use('lazr.editor', 'lp.client.plugins', function (Y) {
                    var widget = new Y.EditableText({
                        contentBox: '#%(id)s',
                    });
                    widget.editor.plug({
                        fn: Y.lp.client.plugins.PATCHPlugin, cfg: {
                          name: '%(attribute)s',
                          url: '%(context_url)s'}});
                    widget.render();
                });
                </script>
                """ % params)
        return dedent(u"""\
            <h1 id="%(id)s"><span
                class="yui-editable_text-text">%(value)s</span>
                %(trigger)s
            </h1>
            %(activation_script)s
            """ % params)
