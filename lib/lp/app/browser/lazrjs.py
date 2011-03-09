# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Wrappers for lazr-js widgets."""

__metaclass__ = type
__all__ = [
    'BooleanChoiceWidget',
    'EnumChoiceWidget',
    'InlineEditPickerWidget',
    'standard_text_html_representation',
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

from lazr.enum import IEnumeratedType
from lazr.restful.declarations import LAZR_WEBSERVICE_EXPORTED
from canonical.lazr.utils import get_current_browser_request
from canonical.lazr.utils import safe_hasattr

from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.vocabulary import IHugeVocabulary
from lp.app.browser.stringformatter import FormattersAPI
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
        self.json_attribute = simplejson.dumps(self.api_attribute)

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


class EditableWidgetBase(WidgetBase):
    """Adds an edit_url property to WidgetBase."""

    def __init__(self, context, exported_field, content_box_id,
                 edit_view, edit_url):
        super(EditableWidgetBase, self).__init__(
            context, exported_field, content_box_id)
        if edit_url is None:
            edit_url = canonical_url(self.context, view_name=edit_view)
        self.edit_url = edit_url


class TextWidgetBase(EditableWidgetBase):
    """Abstract base for the single and multiline text editor widgets."""

    def __init__(self, context, exported_field, title, content_box_id,
                 edit_view, edit_url):
        super(TextWidgetBase, self).__init__(
            context, exported_field, content_box_id, edit_view, edit_url)
        self.accept_empty = simplejson.dumps(self.optional_field)
        self.title = title
        self.widget_css_selector = simplejson.dumps('#' + self.content_box_id)

    @property
    def json_attribute_uri(self):
        return simplejson.dumps(self.resource_uri + '/' + self.api_attribute)


class DefinedTagMixin:
    """Mixin class to define open and closing tags."""

    @property
    def open_tag(self):
        return '<%s id="%s">' % (self.tag, self.content_box_id)

    @property
    def close_tag(self):
        return '</%s>' % self.tag


class TextLineEditorWidget(TextWidgetBase, DefinedTagMixin):
    """Wrapper for the lazr-js inlineedit/editor.js widget."""

    __call__ = ViewPageTemplateFile('../templates/text-line-editor.pt')

    def __init__(self, context, exported_field, title, tag,
                 content_box_id=None, edit_view="+edit", edit_url=None,
                 default_text=None, initial_value_override=None, width=None):
        """Create a widget wrapper.

        :param context: The object that is being edited.
        :param exported_field: The attribute being edited. This should be
            a field from an interface of the form ISomeInterface['fieldname']
        :param title: The string to use as the link title.
        :param tag: The HTML tag to use.
        :param content_box_id: The HTML id to use for this widget.
            Defaults to edit-<attribute name>.
        :param edit_view: The view name to use to generate the edit_url if
            one is not specified.
        :param edit_url: The URL to use for editing when the user isn't logged
            in and when JS is off.  Defaults to the edit_view on the context.
        :param default_text: Text to show in the unedited field, if the
            parameter value is missing or None.
        :param initial_value_override: Use this text for the initial edited
            field value instead of the attribute's current value.
        :param width: Initial widget width.
        """
        super(TextLineEditorWidget, self).__init__(
            context, exported_field, title, content_box_id,
            edit_view, edit_url)
        self.tag = tag
        self.default_text = default_text
        self.initial_value_override = simplejson.dumps(initial_value_override)
        self.width = simplejson.dumps(width)

    @property
    def value(self):
        text = getattr(self.context, self.attribute_name, self.default_text)
        if text is None:
            text = self.default_text
        return text


class TextAreaEditorWidget(TextWidgetBase):
    """Wrapper for the multine-line lazr-js inlineedit/editor.js widget."""

    __call__ = ViewPageTemplateFile('../templates/text-area-editor.pt')

    def __init__(self, context, exported_field, title, content_box_id=None,
                 edit_view="+edit", edit_url=None,
                 hide_empty=True, linkify_text=True):
        """Create the widget wrapper.

        :param context: The object that is being edited.
        :param exported_field: The attribute being edited. This should be
            a field from an interface of the form ISomeInterface['fieldname']
        :param title: The string to use as the link title.
        :param content_box_id: The HTML id to use for this widget.
            Defaults to edit-<attribute name>.
        :param edit_view: The view name to use to generate the edit_url if
            one is not specified.
        :param edit_url: The URL to use for editing when the user isn't logged
            in and when JS is off.  Defaults to the edit_view on the context.
        :param hide_empty: If the attribute has no value, or is empty, then
            hide the editor by adding the "unseen" CSS class.
        :param linkify_text: If True the HTML version of the text will have
            things that look like links made into anchors.
        """
        super(TextAreaEditorWidget, self).__init__(
            context, exported_field, title, content_box_id,
            edit_view, edit_url)
        self.hide_empty = hide_empty
        self.linkify_text = linkify_text

    @property
    def tag_class(self):
        """The CSS class for the widget."""
        classes = ['lazr-multiline-edit']
        if self.hide_empty and not self.value:
            classes.append('unseen')
        return ' '.join(classes)

    @cachedproperty
    def value(self):
        text = getattr(self.context, self.attribute_name, None)
        return standard_text_html_representation(text, self.linkify_text)


class InlineEditPickerWidget(WidgetBase):
    """Wrapper for the lazr-js picker widget.

    This widget is not for editing form values like the
    VocabularyPickerWidget.
    """

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
        return dict(
            header=self.header, step_title=self.step_title,
            remove_button_text=self.remove_button_text,
            null_display_value=self.null_display_value,
            show_remove_button=self.optional_field,
            show_assign_me_button=self.show_assign_me_button,
            show_search_box=self.show_search_box)

    @property
    def json_config(self):
        return simplejson.dumps(self.config)

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


def standard_text_html_representation(value, linkify_text=True):
    """Render a string for html display.

    For this we obfuscate email and render as html.
    """
    if value is None:
        return ''
    nomail = FormattersAPI(value).obfuscate_email()
    return FormattersAPI(nomail).text_to_html(linkify_text=linkify_text)


class BooleanChoiceWidget(EditableWidgetBase, DefinedTagMixin):
    """A ChoiceEdit for a boolean field."""

    __call__ = ViewPageTemplateFile('../templates/boolean-choice-widget.pt')

    def __init__(self, context, exported_field,
                 tag, false_text, true_text, prefix=None,
                 edit_view="+edit", edit_url=None,
                 content_box_id=None, header='Select an item'):
        """Create a widget wrapper.

        :param context: The object that is being edited.
        :param exported_field: The attribute being edited. This should be
            a field from an interface of the form ISomeInterface['fieldname']
        :param tag: The HTML tag to use.
        :param false_text: The string to show for a false value.
        :param true_text: The string to show for a true value.
        :param prefix: Optional text to show before the value.
        :param edit_view: The view name to use to generate the edit_url if
            one is not specified.
        :param edit_url: The URL to use for editing when the user isn't logged
            in and when JS is off.  Defaults to the edit_view on the context.
        :param content_box_id: The HTML id to use for this widget. Automatically
            generated if this is not provided.
        :param header: The large text at the top of the choice popup.
        """
        super(BooleanChoiceWidget, self).__init__(
            context, exported_field, content_box_id, edit_view, edit_url)
        self.header = header
        self.tag = tag
        self.prefix = prefix
        self.true_text = true_text
        self.false_text = false_text
        self.current_value = getattr(self.context, self.attribute_name)

    @property
    def value(self):
        if self.current_value:
            return self.true_text
        else:
            return self.false_text

    @property
    def config(self):
        return dict(
            contentBox='#'+self.content_box_id,
            value=self.current_value,
            title=self.header,
            items=[
                dict(name=self.true_text, value=True, style='', help='',
                     disabled=False),
                dict(name=self.false_text, value=False, style='', help='',
                     disabled=False)])

    @property
    def json_config(self):
        return simplejson.dumps(self.config)


class EnumChoiceWidget(EditableWidgetBase):
    """A popup choice widget."""

    __call__ = ViewPageTemplateFile('../templates/enum-choice-widget.pt')

    def __init__(self, context, exported_field, header,
                 content_box_id=None, enum=None,
                 edit_view="+edit", edit_url=None,
                 css_class_prefix=''):
        super(EnumChoiceWidget, self).__init__(
            context, exported_field, content_box_id, edit_view, edit_url)
        self.header = header
        value = getattr(self.context, self.attribute_name)
        self.css_class = "value %s%s" % (css_class_prefix, value.name)
        self.value = value.title
        if enum is None:
            # Get the enum from the exported field.
            enum = exported_field.vocabulary
        if IEnumeratedType(enum, None) is None:
            raise ValueError('%r does not provide IEnumeratedType' % enum)
        self.items = vocabulary_to_choice_edit_items(enum, css_class_prefix)

    @property
    def config(self):
        return dict(
            contentBox='#'+self.content_box_id,
            value=self.value,
            title=self.header,
            items=self.items)

    @property
    def json_config(self):
        return simplejson.dumps(self.config)
