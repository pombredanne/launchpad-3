# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from StringIO import StringIO

from zope.interface import implements
from zope.component import getUtility
from zope.app.content_types import guess_content_type
from zope.app.form import CustomWidgetFactory
from zope.app.form.browser.widget import SimpleInputWidget
from zope.app.form.browser import FileWidget
from zope.app.form.interfaces import ValidationError, WidgetInputError
from zope.formlib import form
from zope.schema import Bytes, Choice
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.launchpad.webapp.interfaces import IAlwaysSubmittedWidget
from canonical.launchpad.interfaces.librarian import (
    ILibraryFileAlias, ILibraryFileAliasSet)
from canonical.launchpad.fields import KEEP_SAME_IMAGE
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.widgets.itemswidgets import LaunchpadRadioWidget
from canonical.launchpad import _


class LaunchpadFileWidget(FileWidget):
    """A FileWidget which doesn't enclose itself in <div> tags."""

    def _div(self, cssClass, contents, **kw):
        return contents


class ImageChangeWidget(SimpleInputWidget):
    """Widget for changing an existing image.

    This widget should be used only on edit forms.
    """

    implements(IAlwaysSubmittedWidget)
    
    # The LibraryFileAlias representing the user-uploaded image, if any.
    _image_file_alias = None

    def __init__(self, context, request):
        SimpleInputWidget.__init__(self, context, request)
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
        if self.context.getCurrentImage() is not None:
            action_names = [('keep', 'Keep your selected image'),
                            ('delete', 'Change back to default image'),
                            ('change', 'Change to')]
        else:
            action_names = [('keep', 'Leave as default image'),
                            ('change', 'Change to')]
        terms = [SimpleTerm(name, name, label) for name, label in action_names]
        return SimpleVocabulary(terms)

    def getInputValue(self):
        self._error = None
        action = self.action_widget.getInputValue()
        form = self.request.form
        if action == 'change' and not form.get(self.image_widget.name):
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please specify the image you want to use.')))
            raise self._error
        if action == "keep":
            return KEEP_SAME_IMAGE
        elif action == "change":
            image = form.get(self.image_widget.name)
            try:
                self.context.validate(image)
            except ValidationError, v:
                self._error = WidgetInputError(self.name, self.label, v)
                raise self._error
            image.seek(0)
            content = image.read()
            filename = image.filename
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


class ImageAddWidget(ImageChangeWidget):
    """Widget for adding an image.

    This widget should be used only on add forms.
    """

    def _getActionsVocabulary(self):
        action_names = [
            ('keep', 'Leave as default image (you can change it later)'),
            ('change', 'Use this one')]
        terms = [SimpleTerm(name, name, label) for name, label in action_names]
        return SimpleVocabulary(terms)

