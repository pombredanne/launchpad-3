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

    def __init__(self, value, edit_url):
        """Create a widget wrapper.

        :param value: The initial value for the widget.
        :param edit_url: The non-AJAXy URL where this value can be edited.
        """
        self.value = value
        self.edit_url = edit_url

    def __call__(self):
        """Return the HTML to include to render the widget."""
        params = {
            'value': self.value,
            'edit_url': self.edit_url,
            'activation_script': '',
            }
        if getUtility(ILaunchBag).user:
            params['activation_script'] = dedent(u"""\
                <script>
                    YUI().use('lazr.editor', function (Y) {

                    });
                </script>
                """)
        return dedent(u"""\
            <h1><span class="editable-text">%(value)s</span>
                <a href="%(edit_url)s" class="edit-button"
                ><img src="/@@/edit" alt="[edit]" title="Edit" /></a>
            </h1>
            %(activation_script)s
            """ % params)
