# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from StringIO import StringIO

from zope.component import getUtility
from zope.contenttype import guess_content_type
from zope.formlib import form
from zope.formlib.interfaces import WidgetInputError
from zope.formlib.widget import (
    CustomWidgetFactory,
    SimpleInputWidget,
    )
from zope.formlib.widgets import FileWidget
from zope.interface import implementer
from zope.schema import (
    Bytes,
    Choice,
    )
from zope.schema.interfaces import ValidationError
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from lp import _
from lp.app.validators import LaunchpadValidationError
from lp.app.widgets.itemswidgets import LaunchpadRadioWidget
from lp.services.fields import KEEP_SAME_IMAGE
from lp.services.librarian.interfaces import (
    ILibraryFileAlias,
    ILibraryFileAliasSet,
    )
from lp.services.webapp.interfaces import IAlwaysSubmittedWidget


class LaunchpadFileWidget(FileWidget):
    """A FileWidget which doesn't enclose itself in <div> tags."""

    def _div(self, cssClass, contents, **kw):
        return contents


@implementer(IAlwaysSubmittedWidget)
class ImageChangeWidget(SimpleInputWidget):
    """Widget for changing an existing image.

    This widget should be used only on edit forms.
    """

    EDIT_STYLE = 'editview'
    ADD_STYLE = 'addview'

    # The LibraryFileAlias representing the user-uploaded image, if any.
    _image_file_alias = None
    # The user-uploaded image itself, if any.
    _image = None

    def __init__(self, context, request, style):
        SimpleInputWidget.__init__(self, context, request)
        self.style = style
        fields = form.Fields(
            Choice(__name__='action', source=self._getActionsVocabulary(),
                   title=_('Action')),
            Bytes(__name__='image', title=_('Image')))
        fields['action'].custom_widget = CustomWidgetFactory(
            LaunchpadRadioWidget)
        fields['image'].custom_widget = CustomWidgetFactory(
            LaunchpadFileWidget, displayWidth=15)
        widgets = form.setUpWidgets(
            fields, self.name, context, request, ignore_request=False,
            data={'action': 'keep'})
        self.action_widget = widgets['action']
        self.image_widget = widgets['image']

    def __call__(self):
        img = self.context.getCurrentImage()
        if img is not None:
            # This widget is meant to be used only by fields which expect an
            # object implementing ILibraryFileAlias as their values.
            assert ILibraryFileAlias.providedBy(img)
            url = img.getURL()
        else:
            url = self.context.default_image_resource
        html = ('<div><img id="%s" src="%s" alt="%s" /></div>\n'
                % ('%s_current_img' % self.name, url, self.context.title))
        html += "%s\n%s" % (self.action_widget(), self.image_widget())
        return html

    def hasInput(self):
        return self.action_widget.hasInput()

    def _getActionsVocabulary(self):
        if self.style == self.ADD_STYLE:
            action_names = [
                ('keep', 'Leave as default image (you can change it later)'),
                ('change', 'Use this one')]
        elif self.style == self.EDIT_STYLE:
            if self.context.getCurrentImage() is not None:
                action_names = [('keep', 'Keep your selected image'),
                                ('delete', 'Change back to default image'),
                                ('change', 'Change to')]
            else:
                action_names = [('keep', 'Leave as default image'),
                                ('change', 'Change to')]
        else:
            raise AssertionError(
                "Style must be one of EDIT_STYLE or ADD_STYLE, got %s"
                % self.style)
        terms = [SimpleTerm(name, name, label) for name, label in action_names]
        return SimpleVocabulary(terms)

    def getInputValue(self):
        self._error = None
        action = self.action_widget.getInputValue()
        form = self.request.form_ng
        if action == 'change' and not form.getOne(self.image_widget.name):
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please specify the image you want to use.')))
            raise self._error
        if action == "keep":
            if self.style == self.ADD_STYLE:
                # It doesn't make any sense to return KEEP_SAME_IMAGE in this
                # case, since there's nothing to keep.
                return None
            elif self.style == self.EDIT_STYLE:
                return KEEP_SAME_IMAGE
            else:
                raise AssertionError(
                    "Style must be one of EDIT_STYLE or ADD_STYLE, got %s"
                    % self.style)
        elif action == "change":
            self._image = form.getOne(self.image_widget.name)
            try:
                self.context.validate(self._image)
            except ValidationError as v:
                self._error = WidgetInputError(self.name, self.label, v)
                raise self._error
            self._image.seek(0)
            content = self._image.read()
            filename = self._image.filename
            type, dummy = guess_content_type(name=filename, body=content)

            # This method may be called more than once in a single request. If
            # that's the case here we'll simply return the cached
            # LibraryFileAlias we already have.
            existing_alias = self._image_file_alias
            if existing_alias is not None:
                assert existing_alias.filename == filename, (
                    "The existing LibraryFileAlias' name doesn't match the "
                    "given image's name.")
                assert existing_alias.content.filesize == len(content), (
                    "The existing LibraryFileAlias' size doesn't match "
                    "the given image's size.")
                assert existing_alias.mimetype == type, (
                    "The existing LibraryFileAlias' type doesn't match "
                    "the given image's type.")
                return existing_alias

            self._image_file_alias = getUtility(ILibraryFileAliasSet).create(
                name=filename, size=len(content), file=StringIO(content),
                contentType=type)
            return self._image_file_alias
        elif action == "delete":
            return None
