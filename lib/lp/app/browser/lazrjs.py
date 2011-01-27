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

import simplejson

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.security.checker import canAccess, canWrite
from zope.schema.interfaces import IVocabulary
from zope.schema.vocabulary import getVocabularyRegistry

from lazr.restful.declarations import LAZR_WEBSERVICE_EXPORTED
from canonical.lazr.utils import get_current_browser_request
from canonical.lazr.utils import safe_hasattr

from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.vocabulary import IHugeVocabulary
from lp.services.propertycache import cachedproperty


class WidgetBase:
    """Useful methods for all widgets."""

    def __init__(self, context, exported_field, content_box_id):
        self.context = context
        self.exported_field = exported_field

        self.request = get_current_browser_request()
        self.attribute_name = exported_field.__name__
        self.optional_field = not exported_field.required

        if content_box_id is None:
            content_box_id = "edit-%s" % self.attribute_name
        self.content_box_id = content_box_id

        # The mutator method name is used to determine whether or not the
        # current user has permission to alter the attribute if the attribute
        # is using a mutator function.
        self.mutator_method_name = None
        ws_stack = exported_field.queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)
        if ws_stack is None:
            # The field may be a copy, or similarly named to one we care
            # about.
            self.api_attribute = self.attribute_name
        else:
            self.api_attribute = ws_stack['as']
            mutator_info = ws_stack.get('mutator_annotations')
            if mutator_info is not None:
                mutator_method, mutator_extra = mutator_info
                self.mutator_method_name = mutator_method.__name__

    @property
    def resource_uri(self):
        """A local path to the context object.

        The javascript uses the normalize_uri method that adds the appropriate
        prefix to the uri.  Doing it this way avoids needing to adapt the
        current request into a webservice request in order to get an api url.
        """
        return canonical_url(self.context, force_local_path=True)

    @property
    def json_resource_uri(self):
        return simplejson.dumps(self.resource_uri)

    @property
    def can_write(self):
        """Can the current user write to the attribute."""
        if canWrite(self.context, self.attribute_name):
            return True
        elif self.mutator_method_name is not None:
            # The user may not have write access on the attribute itself, but
            # the REST API may have a mutator method configured, such as
            # transitionToAssignee.
            return canAccess(self.context, self.mutator_method_name)
        else:
            return False


class TextWidgetBase(WidgetBase):
    """Abstract base for the single and multiline text editor widgets."""

    def __init__(self, context, exported_field, content_box_id,
                 title, edit_view, edit_url):
        super(TextWidgetBase, self).__init__(
            context, exported_field, content_box_id)
        if edit_url is None:
            edit_url = canonical_url(self.context, view_name=edit_view)
        self.edit_url = edit_url
        self.accept_empty = simplejson.dumps(self.optional_field)
        self.title = title
        self.json_attribute = simplejson.dumps(self.api_attribute)
        self.widget_css_selector = simplejson.dumps('#' + self.content_box_id)

    @property
    def json_attribute_uri(self):
        return simplejson.dumps(self.resource_uri + '/' + self.api_attribute)


class TextLineEditorWidget(TextWidgetBase):
    """Wrapper for the lazr-js inlineedit/editor.js widget."""

    __call__ = ViewPageTemplateFile('../templates/text-line-editor.pt')

    def __init__(self, context, exported_field, content_box_id=None,
                 title="Edit",
                 tag='h1', edit_view="+edit", edit_url=None,
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
        :param default_text: Text to show in the unedited field, if the
            parameter value is missing or None.
        :param initial_value_override: Use this text for the initial edited
            field value instead of the attribute's current value.
        :param width: Initial widget width.
        """
        super(TextLineEditorWidget, self).__init__(
            context, exported_field, content_box_id,
            title, edit_view, edit_url)
        self.tag = tag
        self.default_text = default_text
        self.initial_value_override = simplejson.dumps(initial_value_override)
        self.width = simplejson.dumps(width)

    @property
    def open_tag(self):
        return '<%s id="%s">' % (self.tag, self.content_box_id)

    @property
    def close_tag(self):
        return '</%s>' % self.tag

    @property
    def value(self):
        text = getattr(self.context, self.attribute_name, self.default_text)
        if text is None:
            text = self.default_text
        return text


class TextAreaEditorWidget(TextWidgetBase):
    """Wrapper for the multine-line lazr-js inlineedit/editor.js widget."""

    __call__ = ViewPageTemplateFile('../templates/text-area-editor.pt')

    def __init__(self, context, exported_field, content_box_id=None,
                 title="Edit", value=None,
                 edit_view="+edit", edit_url=None, visible=True):
        """Create the widget wrapper."""
        super(TextAreaEditorWidget, self).__init__(
            context, exported_field, content_box_id,
            title, edit_view, edit_url)
        self.value = value
        if visible:
            self.tag_class = 'lazr-multiline-edit'
        else:
            self.tag_class = 'lazr-multiline-edit unseen'



class InlineEditPickerWidget(WidgetBase):
    """Wrapper for the lazr-js picker widget.

    This widget is not for editing form values like the
    VocabularyPickerWidget.
    """

    widget_type = 'inline-picker-activator'
    __call__ = ViewPageTemplateFile('../templates/inline-picker.pt')

    def __init__(self, context, exported_field, default_html,
                 content_box_id=None, header='Select an item',
                 step_title='Search', remove_button_text='Remove',
                 null_display_value='None'):
        """Create a widget wrapper.

        :param context: The object that is being edited.
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
        super(InlineEditPickerWidget, self).__init__(
            context, exported_field, content_box_id)
        self.default_html = default_html
        self.header = header
        self.step_title = step_title
        self.remove_button_text = remove_button_text
        self.null_display_value = null_display_value

        # JSON encoded attributes.
        self.json_content_box_id = simplejson.dumps(self.content_box_id)
        self.json_attribute = simplejson.dumps(self.api_attribute + '_link')
        self.json_vocabulary_name = simplejson.dumps(
            self.exported_field.vocabularyName)

    @property
    def config(self):
        return simplejson.dumps(
            dict(header=self.header, step_title=self.step_title,
                 remove_button_text=self.remove_button_text,
                 null_display_value=self.null_display_value,
                 show_remove_button=self.optional_field,
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

