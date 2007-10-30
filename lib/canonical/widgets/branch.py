# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Widgets related to IBranch."""

__metaclass__ = type
__all__ = [
    'TargetBranchWidget',
    ]


from zope.app.form import CustomWidgetFactory
from zope.app.form.interfaces import IInputWidget
from zope.app.form.utility import setUpWidget
from zope.app.traversing.interfaces import IPathAdapter
from zope.component import getUtility, queryAdapter
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.launchpad.interfaces import IBranchSet, ILaunchBag
from canonical.launchpad.helpers import shortlist
from canonical.widgets.itemswidgets import LaunchpadRadioWidget
from canonical.widgets.popup import SinglePopupWidget


class TargetBranchWidget(LaunchpadRadioWidget):
    """Widget for selecting a target branch.

    The default branch for a new branch merge proposal should be
    the branch associated with the development focus series if there
    is one (that isn't an import branch).

    Also in the initial radio button selector are other branches for
    the product that the branch owner has specified as target branches
    for other merge proposals.

    Finally therer is an "other" button that gets the user to use the
    normal branch selector.
    """

    _joinButtonToMessageTemplate = u'%s&nbsp;%s'

    def __init__(self, field, vocabulary, request):
        branch = field.context
        self.branch_selector_vocab = self._generateTargetVocab(branch)

        LaunchpadRadioWidget.__init__(
            self, field, self.branch_selector_vocab, request)

        self.other_branch_widget = CustomWidgetFactory(
            SinglePopupWidget, displayWidth=35)
        setUpWidget(
            self, 'other_branch', field, IInputWidget,
            prefix=self.name, context=branch)

    def _generateTargetVocab(self, branch):
        """Generate the vocabulary for the radio buttons."""
        assert(branch.product)
        self.dev_focus = branch.product.development_focus.user_branch
        logged_in_user = getUtility(ILaunchBag).user
        target_branches = shortlist(
            getUtility(IBranchSet).getTargetBranchesForUsersMergeProposals(
                logged_in_user, branch.product))
        if (self.dev_focus is not None and
            not self.dev_focus in target_branches):
            target_branches.insert(0, self.dev_focus)

        terms = []
        for branch in target_branches:
            terms.append(SimpleTerm(
                    branch, branch.unique_name, branch.title))

        return SimpleVocabulary(terms)

    def _toFieldValue(self, form_value):
        if form_value == "other":
            return self.other_branch_widget.getInputValue()
        else:
            term = self.branch_selector_vocab.getTermByToken(form_value)
            return term.value

    def getInputValue(self):
        return self._toFieldValue(self._getFormInput())

    def setRenderedValue(self, value):
        pass
        #self._data = value
        #if value is not self.context.malone_marker:
        #    self.branch_widget.setRenderedValue(value)

    def _renderLabel(self, text, index):
        """Render a label for the option with the specified index."""
        option_id = '%s.%s' % (self.name, index)
        return u'<label for="%s" style="font-weight: normal">%s</label>' % (
            option_id, text)

    def _renderBranchLabel(self, branch, index):
        option_id = '%s.%s' % (self.name, index)

        adapter = queryAdapter(branch, IPathAdapter, 'fmt')
        text = adapter.link('')
        if branch == self.dev_focus:
            text = text + " <em>(development focus)</em>"
        return u'<label for="%s" style="font-weight: normal">%s</label>' % (
            option_id, text)

    def renderItems(self, value):
        field = self.context
        product = field.context
        if value == self._missing:
            value = field.missing_value

        items = []
        index = 0
        # Render each of the branches with the first selected.
        for index, term in enumerate(self.branch_selector_vocab):
            branch = term.value
            if len(items) == 0:
                renderfunc = self.renderSelectedItem
            else:
                renderfunc = self.renderItem

            render_args = dict(
                index=index, text=self._renderBranchLabel(branch, index),
                value=branch.unique_name, name=self.name,
                cssClass=self.cssClass)
            items.append(renderfunc(**render_args))

        # Lastly render the other option.
        index = len(items)
        if index == 0:
            renderfunc = self.renderSelectedItem
        else:
            renderfunc = self.renderItem
        other_branch_text = "%s %s" % (
            self._renderLabel("Other:", index),
            self.other_branch_widget())
        render_args = dict(
            index=index, text=other_branch_text,
            value="other", name=self.name,
            cssClass=self.cssClass)
        items.append(renderfunc(**render_args))

        return items
