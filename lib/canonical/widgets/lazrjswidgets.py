# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Wrappers for lazr-js widgets."""

__metaclass__ = type
__all__ = [
    'InlineTextLineEditorWidget',
    ]

from textwrap import dedent

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import ILaunchBag


class InlineTextLineEditorWidget:
    """Wrapper for the lazr-js inlineedit/editor.js widget."""

    last_id = 0

    def __init__(self, value, edit_url, id=None, title="Edit"):
        """Create a widget wrapper.

        :param value: The initial value for the widget.
        :param edit_url: The non-AJAXy URL where this value can be edited.
        """
        self.value = value
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
            'edit_url': self.edit_url,
            'id': self.id,
            'title': self.title,
            'value': self.value,
            }
        if getUtility(ILaunchBag).user:
            params['activation_script'] = dedent(u"""\
                <script>
                    YUI().use('lazr.editor', function (Y) {

                    });
                </script>
                """)
        return dedent(u"""\
            <h1 id="%(id)s"><span class="editable-text">%(value)s</span>
                <a href="%(edit_url)s" class="edit-button"
                ><img src="/@@/edit" alt="[edit]" title="%(title)s" /></a>
            </h1>
            %(activation_script)s
            """ % params)
