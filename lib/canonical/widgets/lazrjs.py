# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Wrappers for lazr-js widgets."""

__metaclass__ = type
__all__ = [
    'InlineEditPickerWidget',
    'TextAreaEditorWidget',
    'TextLineEditorWidget',
    'vocabulary_to_choice_edit_items',
    ]

import cgi
import simplejson
from textwrap import dedent

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.security.checker import canAccess, canWrite
from zope.schema.interfaces import IVocabulary
from zope.schema.vocabulary import getVocabularyRegistry

from lazr.restful.declarations import LAZR_WEBSERVICE_EXPORTED
from lazr.restful.interfaces import IWebServiceClientRequest
from canonical.lazr.utils import safe_hasattr

from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.vocabulary import IHugeVocabulary
from lp.services.propertycache import cachedproperty


class WidgetBase:
    """Useful methods for all widgets."""

    # Class variable used to generate a unique per-page id for the widget
    # in case it's not provided.
    last_id = 0

    def __init__(self, context, exported_field):
        self.context = context
        self.exported_field = exported_field
        self.attribute_name = exported_field.__name__
        # If there is no webservice tagged versioned dict, there is no point
        # having a widget, so let it explode with a KeyError here.
        ws_stack = exported_field.queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)
        self.api_attribute = ws_stack['as']
        mutator_info = ws_stack.get('mutator_annotations')
        if mutator_info is not None:
            mutator_method, mutator_extra = mutator_info
            self.mutator_method_name = mutator_method.__name__
        else:
            self.mutator_method_name = None
        self.resource_uri = canonical_url(self.context, force_local_path=True)

    @classmethod
    def _generate_id(cls):
        """Return a presumably unique id for this widget."""
        cls.last_id += 1
        return '%s-id-%d' % (cls.widget_type, cls.last_id)

    @property
    def can_write(self):
        if canWrite(self.context, self.attribute_name):
            return True
        elif self.mutator_method_name is not None:
            # The user may not have write access on the attribute itself, but
            # the REST API may have a mutator method configured, such as
            # transitionToAssignee.
            return canAccess(self.context, self.mutator_method_name)
        else:
            return False


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
        <%(tag)s id="%(id)s"><span
            class="yui3-editable_text-text">%(value)s</span>
            %(trigger)s
        </%(tag)s>
        %(activation_script)s
        """)

    # Template for the trigger button.
    TRIGGER_TEMPLATE = dedent(u"""\
        <a href="%(edit_url)s" class="yui3-editable_text-trigger sprite edit"
        ></a>
        """)

    # Template for the activation script.
    ACTIVATION_TEMPLATE = dedent(u"""\
        <script>
        LPS.use('lazr.editor', 'lp.client.plugins', function (Y) {
            var widget = new Y.EditableText({
                contentBox: '#%(id)s',
                accept_empty: %(accept_empty)s,
                width: '%(width)s',
                initial_value_override: %(initial_value_override)s
            });
            widget.editor.plug({
                fn: Y.lp.client.plugins.PATCHPlugin, cfg: {
                  patch: '%(public_attribute)s',
                  resource: '%(context_url)s'}});
            widget.render();
        });
        </script>
        """)

    def __init__(self, context, attribute, edit_url, id=None, title="Edit",
                 tag='h1', public_attribute=None, accept_empty=False,
                 default_text=None, initial_value_override=None, width=None):
        """Create a widget wrapper.

        :param context: The object that is being edited.
        :param attribute: The name of the attribute being edited.
        :param edit_url: The URL to use for editing when the user isn't logged
            in and when JS is off.
        :param id: The HTML id to use for this widget. Automatically
            generated if this is not provided.
        :param title: The string to use as the link title. Defaults to 'Edit'.
        :param tag: The HTML tag to use.
        :param public_attribute: If given, the name of the attribute in the
            public webservice API.
        :param accept_empty: Whether the field accepts empty input or not.
        :param default_text: Text to show in the unedited field, if the
            parameter value is missing or None.
        :param initial_value_override: Use this text for the initial edited
            field value instead of the attribute's current value.
        :param width: Initial widget width.
        """
        self.context = context
        self.attribute = attribute
        self.edit_url = edit_url
        self.tag = tag
        if accept_empty:
            self.accept_empty = 'true'
        else:
            self.accept_empty = 'false'
        if public_attribute is None:
            self.public_attribute = attribute
        else:
            self.public_attribute = public_attribute
        if id is None:
            self.id = self._generate_id()
        else:
            self.id = id
        self.title = title
        self.default_text = default_text
        self.initial_value_override = initial_value_override
        self.width = width

    @classmethod
    def _generate_id(cls):
        """Return a presumably unique id for this widget."""
        cls.last_id += 1
        return 'inline-textline-editor-id%d' % cls.last_id

    def __call__(self):
        """Return the HTML to include to render the widget."""
        # We can't use the value None because of the cgi.escape() and because
        # that wouldn't look very good in the ui!
        value = getattr(self.context, self.attribute, self.default_text)
        if value is None:
            value = self.default_text
        params = {
            'activation_script': '',
            'trigger': '',
            'edit_url': self.edit_url,
            'id': self.id,
            'title': self.title,
            'value': cgi.escape(value),
            'context_url': canonical_url(
                self.context, path_only_if_possible=True),
            'attribute': self.attribute,
            'tag': self.tag,
            'public_attribute': self.public_attribute,
            'accept_empty': self.accept_empty,
            'initial_value_override': simplejson.dumps(
                self.initial_value_override),
            'width': self.width,
            }
        # Only display the trigger link and the activation script if
        # the user can write the attribute.
        if canWrite(self.context, self.attribute):
            params['trigger'] = self.TRIGGER_TEMPLATE % params
            params['activation_script'] = self.ACTIVATION_TEMPLATE % params
        return self.WIDGET_TEMPLATE % params 


class TextAreaEditorWidget(TextLineEditorWidget):
    """Wrapper for the multine-line lazr-js inlineedit/editor.js widget."""

    def __init__(self, *args, **kwds):
        """Create the widget wrapper."""
        if 'value' in kwds:
            self.value = kwds.get('value', '')
            kwds.pop('value')
        super(TextAreaEditorWidget, self).__init__(*args, **kwds)

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
        <div id="multi-text-editor">
          <div class="clearfix">
            %(edit_controls)s
            <h2>%(title)s</h2>
          </div>
          <div class="yui3-editable_text-text">%(value)s</div>
        </div>
        %(activation_script)s
        """)

    CONTROLS_TEMPLATE = dedent(u"""\
        <div class="edit-controls">
          &nbsp;
          %(trigger)s
        </div>
        """)

    ACTIVATION_TEMPLATE = dedent(u"""\
        <script>
        LPS.use('lazr.editor', 'lp.client.plugins', function (Y) {
            var widget = new Y.EditableText({
                contentBox: '#%(id)s',
                accept_empty: %(accept_empty)s,
                multiline: true,
                buttons: 'top'
            });
            widget.editor.plug({
                fn: Y.lp.client.plugins.PATCHPlugin, cfg: {
                  patch: '%(attribute)s',
                  resource: '%(context_url)s/%(attribute)s',
                  patch_field: true,
                  accept: 'application/xhtml+xml'
            }});
            if (!Y.UA.opera) {
                widget.render();
            }
            var lpns = Y.namespace('lp');
            if (!lpns.widgets) {
                lpns.widgets = {};
            }
            lpns.widgets['%(id)s'] = widget;
        });
        </script>
        """)

    def __call__(self):
        """Return the HTML to include to render the widget."""
        params = {
            'activation_script': '',
            'trigger': '',
            'edit_url': self.edit_url,
            'id': self.id,
            'title': self.title,
            'value': self.value,
            'context_url': canonical_url(
                self.context, path_only_if_possible=True),
            'attribute': self.attribute,
            'accept_empty': self.accept_empty,
            'edit_controls': '',
            }
        # Only display the trigger link and the activation script if
        # the user can write the attribute.
        if canWrite(self.context, self.attribute):
            params['trigger'] = self.TRIGGER_TEMPLATE % params
            params['activation_script'] = self.ACTIVATION_TEMPLATE % params
            params['edit_controls'] = self.CONTROLS_TEMPLATE % params
        return self.WIDGET_TEMPLATE % params


class InlineEditPickerWidget(WidgetBase):
    """Wrapper for the lazr-js picker widget.

    This widget is not for editing form values like the
    VocabularyPickerWidget.
    """

    widget_type = 'inline-picker-activator'
    __call__ = ViewPageTemplateFile('templates/inline-picker.pt')

    def __init__(self, context, request, exported_field, default_html,
                 content_box_id, header='Select an item',
                 step_title='Search', remove_button_text='Remove',
                 null_display_value='None'):
        """Create a widget wrapper.

        :param context: The object that is being edited.
        :param request: The request object.
        :param exported_field: The attribute being edited. This should be
            a field from an interface of the form ISomeInterface['fieldname']
        :param default_html: Default display of attribute.
        :param content_box_id: The HTML id to use for this widget. Automatically
            generated if this is not provided.
        :param header: The large text at the top of the picker.
        :param step_title: Smaller line of text below the header.
        :param remove_button_text: Override default button text: "Remove"
        :param null_display_value: This will be shown for a missing value
        """
        super(InlineEditPickerWidget, self).__init__(context, exported_field)
        self.request = request
        self.default_html = default_html
        self.content_box_id = content_box_id
        self.header = header
        self.step_title = step_title
        self.remove_button_text = remove_button_text
        self.null_display_value = null_display_value

        # JSON encoded attributes.
        self.json_resource_uri = simplejson.dumps(self.resource_uri)
        self.json_content_box_id = simplejson.dumps(self.content_box_id)
        self.json_attribute = simplejson.dumps(self.api_attribute + '_link')
        self.json_vocabulary_name = simplejson.dumps(
            self.exported_field.vocabularyName)
        self.show_remove_button = not self.exported_field.required

    @property
    def config(self):
        return simplejson.dumps(
            dict(header=self.header, step_title=self.step_title,
                 remove_button_text=self.remove_button_text,
                 null_display_value=self.null_display_value,
                 show_remove_button=self.show_remove_button,
                 show_assign_me_button=self.show_assign_me_button,
                 show_search_box=self.show_search_box))

    @cachedproperty
    def vocabulary(self):
        registry = getVocabularyRegistry()
        return registry.get(
            IVocabulary, self.exported_field.vocabularyName)

    @property
    def show_search_box(self):
        return IHugeVocabulary.providedBy(self.vocabulary)

    @property
    def show_assign_me_button(self):
        # show_assign_me_button is true if user is in the vocabulary.
        vocabulary = self.vocabulary
        user = getUtility(ILaunchBag).user
        return user and user in vocabulary


def vocabulary_to_choice_edit_items(
    vocab, css_class_prefix=None, disabled_items=None, as_json=False,
    name_fn=None, value_fn=None):
    """Convert an enumerable to JSON for a ChoiceEdit.

    :vocab: The enumeration to iterate over.
    :css_class_prefix: If present, append this to an item's value to create
        the css_class property for it.
    :disabled_items: A list of items that should be displayed, but disabled.
    :name_fn: A function receiving an item and returning its name.
    :value_fn: A function receiving an item and returning its value.
    """
    if disabled_items is None:
        disabled_items = []
    items = []
    for item in vocab:
        # Introspect to make sure we're dealing with the object itself.
        # SimpleTerm objects have the object itself at item.value.
        if safe_hasattr(item, 'value'):
            item = item.value
        if name_fn is not None:
            name = name_fn(item)
        else:
            name = item.title
        if value_fn is not None:
            value = value_fn(item)
        else:
            value = item.title
        new_item = {
            'name': name,
            'value': value,
            'style': '', 'help': '', 'disabled': False}
        for disabled_item in disabled_items:
            if disabled_item == item:
                new_item['disabled'] = True
                break
        if css_class_prefix is not None:
            new_item['css_class'] = css_class_prefix + item.name
        items.append(new_item)

    if as_json:
        return simplejson.dumps(items)
    else:
        return items

