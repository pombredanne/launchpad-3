
from zope.app.form import CustomWidgetFactory
from zope.app.form.browser import BrowserWidget
from zope.formlib import form
from zope.schema import Bytes, Choice
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.widgets.itemswidgets import LaunchpadRadioWidget
from canonical.launchpad import _


class ImageWidget(BrowserWidget):
    """Widget for uploading an image or deleting an existing one."""

    def __init__(self, context, request):
        BrowserWidget.__init__(self, context, request)
        fields = form.Fields(
            Choice(__name__='action', source=self._getActionsVocabulary(),
                   title=_('Action')),
            Bytes(__name__='image', title=_('Image')))
        fields['action'].custom_widget = CustomWidgetFactory(
            LaunchpadRadioWidget, orientation='horizontal')
        self.widgets = form.setUpWidgets(
            fields, self.name, context, request, ignore_request=False,
            data={'action': 'keep'})

    def __call__(self):
        img = getattr(self.context.context, self.context.__name__, None)
        if img is not None:
            # XXX: Assuming that the image has a 'url' attribute is not a good
            # idea. What are the alternatives?
            url = img.url
        else:
            url = self.context.default_image_resource
        html = '<img src="%s" alt="%s" />\n' % (url, self.context.title)
        html += "%s\n%s" % (self.widgets['action'](), self.widgets['image']())
        return html

    def _getActionsVocabulary(self):
        action_names = [
            ('keep', 'Keep'), ('delete', 'Delete'), ('change', 'Change to')]
        terms = [SimpleTerm(name, name, label) for name, label in action_names]
        return SimpleVocabulary(terms)

    def getInputValue(self):
        action = self.widgets['action'].getInputValue()
        if action == "keep":
            return self.context.keep_image_marker
        elif action == "change":
            return self.widgets['image'].getInputValue()
        elif action == "delete":
            return None

