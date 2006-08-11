# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Views for IBugLinkTarget."""

__metaclass__ = type

__all__ = [
    'BugLinkView',
    'BugsUnlinkView',
    ]

from zope.event import notify
from zope.formlib import form
from zope.interface import implements, Interface, providedBy
from zope.schema import Choice, Set
from zope.schema.interfaces import IChoice, IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from zope.app.form import CustomWidgetFactory
from zope.app.form.browser import MultiCheckBoxWidget
from zope.app.form.browser.widget import renderElement
from zope.app.pagetemplate import ViewPageTemplateFile

from canonical.launchpad import _
from canonical.launchpad.event import SQLObjectModifiedEvent
from canonical.launchpad.fields import BugField
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.snapshot import Snapshot


# XXX flacoste 2006/08/02 This should be moved to canonical.launchpad.webapp
# or canonical.widgets. It wasn't done yet because that code is copied
# from my tt-search branch which hasn't landed yet.
class XHTMLCompliantMultiCheckBoxWidget(MultiCheckBoxWidget):
    """MultiCheckBoxWidget which wraps option labels with proper <label> elements."""

    def __init__(self, field, vocabulary, request):
        # XXXX flacoste 2006/07/23 Workaround Zope3 bug #545:
        # CustomWidgetFactory passes wrong arguments to a MultiCheckBoxWidget
        if IChoice.providedBy(vocabulary):
            vocabulary = vocabulary.vocabulary
        MultiCheckBoxWidget.__init__(self, field, vocabulary, request)

    def renderItem(self, index, text, value, name, cssClass):
        id = '%s.%s' % (name, index)
        label = '<label style="font-weight: normal" for="%s">%s</label>' % (
            id, text)
        elem = renderElement('input',
                             type="checkbox",
                             cssClass=cssClass,
                             name=name,
                             id=id,
                             value=value)
        return self._joinButtonToMessageTemplate %(elem, label)

    def renderSelectedItem(self, index, text, value, name, cssClass):
        id = '%s.%s' % (name, index)
        label = '<label style="font-weight: normal" for="%s">%s</label>' % (
            id, text)
        elem = renderElement('input',
                             type="checkbox",
                             cssClass=cssClass,
                             name=name,
                             id=id,
                             value=value,
                             checked="checked")
        return self._joinButtonToMessageTemplate %(elem, label)


class IBugLinkForm(Interface):
    """Schema for the unlink bugs form."""

    bug = BugField(title=_('Bug ID'), required=True,
        description=_("Enter the Malone bug ID or nickname that "
                      "you want to link to."))


class BugLinkView(form.Form):
    """This view is used to link bugs to any IBugLinkTarget."""

    label = _('Link to bug report')

    form_fields = form.Fields(IBugLinkForm)

    template = ViewPageTemplateFile('../templates/buglinktarget-linkbug.pt')

    def setUpWidgets(self, ignore_request=False):
        super(BugLinkView, self).setUpWidgets(ignore_request=ignore_request)

        self.widgets['bug'].extra = 'tabindex="1"'

    @form.action(_('Link'))
    def linkBug(self, action, data):
        """Link to the requested bug. Publish an SQLObjectModifiedEvent and
        display a notification on the ticket page."""
        response = self.request.response
        target_unmodified = Snapshot(
            self.context, providing=providedBy(self.context))
        bug = data['bug']
        self.context.linkBug(bug)
        bug_props = {'bugid': bug.id, 'title': bug.title}
        # XXX flacoste 2006-08-11 Reenable I18N once
        # bug 54987 is fixed. (Using MessageId with addNotification is broken)
        #response.addNotification(
                #_('Added link to bug #${bugid}: '
                   #'\N{left double quotation mark}${title}'
                   #'\N{right double quotation mark}.', mapping=bug_props))
        response.addNotification(
            'Added link to bug #%(bugid)s: '
            '\N{left double quotation mark}%(title)s'
            '\N{right double quotation mark}.' % bug_props)
        notify(SQLObjectModifiedEvent(
            self.context, target_unmodified, ['bugs']))
        response.redirect(canonical_url(self.context))
        return ''

    @form.action(_('Cancel'), validator='validateCancel')
    def cancel(self, action, data):
        """Redirect the user to the ticket page."""
        self.request.response.redirect(canonical_url(self.context))
        return ''

    def validateCancel(self, action, data):
        """Empty validator"""
        pass


class BugLinksVocabularyFactory(object):
    """IContextSourceBinder that creates a vocabulary of the linked bugs on
    the IBugLinkTarget."""

    implements(IContextSourceBinder)

    def __call__(self, context):
        """See IContextSourceBinder."""
        terms = []
        for bug in context.bugs:
            title = _('#${bugid}: ${title}', mapping={'bugid': bug.id,
                                                     'title': bug.title})
            terms.append(SimpleTerm(bug, bug.id, title))
        return SimpleVocabulary(terms)


class IUnlinkBugsForm(Interface):
    """Schema for the unlink bugs form."""

    bugs = Set(title=_('Bug Links:'), required=True,
               value_type=Choice(source=BugLinksVocabularyFactory()),
               description=_('Select the bug links that you want to remove.'))


class BugsUnlinkView(form.Form):
    """This view is used to remove bug links from any IBugLinkTarget."""

    label = _('Remove links to bug reports')

    form_fields = form.Fields(IUnlinkBugsForm)
    form_fields['bugs'].custom_widget = CustomWidgetFactory(
        XHTMLCompliantMultiCheckBoxWidget)

    template = ViewPageTemplateFile('../templates/buglinktarget-unlinkbugs.pt')

    @form.action(_('Remove'))
    def unlinkBugs(self, action, data):
        response = self.request.response
        target_unmodified = Snapshot(
            self.context, providing=providedBy(self.context))
        for bug in data['bugs']:
            self.context.unlinkBug(bug)
            # XXX flacoste 2006-08-11 Reenable I18N once
            # bug 54987 is fixed. (Using MessageId with addNotification is
            # broken)
            #response.addNotification(
                #_('Removed link to bug #${bugid}.', mapping={'bugid': bug.id}))
            response.addNotification('Removed link to bug #%d.' % bug.id)
        notify(SQLObjectModifiedEvent(
            self.context, target_unmodified, ['bugs']))
        response.redirect(canonical_url(self.context))
        return ''


