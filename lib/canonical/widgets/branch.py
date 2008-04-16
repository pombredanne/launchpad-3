# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Widgets related to IBranch."""

__metaclass__ = type
__all__ = [
    'TargetBranchWidget',
    ]


from zope.app.form.browser.widget import renderElement
from zope.app.form.interfaces import IInputWidget, InputErrors
from zope.app.form.utility import setUpWidget
from zope.component import getMultiAdapter, getUtility
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from canonical.launchpad.interfaces import IBranchSet, ILaunchBag
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.webapp import canonical_url
from canonical.widgets.itemswidgets import LaunchpadRadioWidget


class TargetBranchWidget(LaunchpadRadioWidget):
    """Widget for selecting a target branch.

    The default branch for a new branch merge proposal should be
    the branch associated with the development focus series if there
    is one (that isn't an import branch).

    Also in the initial radio button selector are other branches for
    the product that the branch owner has specified as target branches
    for other merge proposals.

    Finally there is an "other" button that gets the user to use the
    normal branch selector.
    """

    def __init__(self, field, vocabulary, request):
        # Create the vocabulary and pass that to the radio button
        # constructor.
        branch = field.context
        self.branch_selector_vocab = self._generateTargetVocab(branch)

        LaunchpadRadioWidget.__init__(
            self, field, self.branch_selector_vocab, request)

        self.other_branch_widget = getMultiAdapter(
            (field, request), IInputWidget)
        setUpWidget(
            self, 'other_branch', field, IInputWidget,
            prefix=self.name, context=branch)

        # If there are branches to show explicitly, then we want to be
        # able to select the 'Other' selection item when someone types
        # in any values.
        branch_count = len(self.branch_selector_vocab)
        if branch_count > 0:
            on_key_press = "selectWidget('%s.%d', event);" % (
                self.name, branch_count)
            self.other_branch_widget.onKeyPress = on_key_press

    def _generateTargetVocab(self, branch):
        """Generate the vocabulary for the radio buttons.

        The generated vocabulary contains the branch associated with the
        development series of the product if there is one, and also any other
        branches that the user has specified before as a target for a proposed
        merge.
        """
        assert branch.product, "A product is needed to build the vocabulary."
        self.dev_focus = branch.product.development_focus.user_branch
        logged_in_user = getUtility(ILaunchBag).user
        target_branches = shortlist(
            getUtility(IBranchSet).getTargetBranchesForUsersMergeProposals(
                logged_in_user, branch.product))
        # If there is a development focus branch, make sure it is always
        # shown, and as the first item.
        if self.dev_focus is not None and branch != self.dev_focus:
            if self.dev_focus in target_branches:
                target_branches.remove(self.dev_focus)
            target_branches.insert(0, self.dev_focus)

        # Make sure the the source branch isn't in the target_branches.
        if branch in target_branches:
            target_branches.remove(branch)

        terms = []
        for branch in target_branches:
            terms.append(SimpleTerm(
                    branch, branch.unique_name, branch.title))

        return SimpleVocabulary(terms)

    def _toFieldValue(self, form_value):
        """Convert the form value into a branch.

        If there were no radio button options, or 'other' was selected, then
        get the value from the branch widget, otherwise get the branch
        reference from the built up vocabulary.
        """
        if (len(self.branch_selector_vocab) == 0 or
            form_value == "other"):
            # Get the value from the branch selector widget.
            try:
                return self.other_branch_widget.getInputValue()
            except InputErrors:
                self._error = self.other_branch_widget._error
                raise
        else:
            term = self.branch_selector_vocab.getTermByToken(form_value)
            return term.value

    def hasInput(self):
        """Is there any input for the widget.

        We need to defer the call to the other branch widget when either there
        are no terms in the vocabulary or the other radio button was selected.
        """
        if len(self.branch_selector_vocab) == 0:
            return self.other_branch_widget.hasInput()
        else:
            has_input = LaunchpadRadioWidget.hasInput(self)
            if has_input:
                if self._getFormInput() == "other":
                    return self.other_branch_widget.hasInput()
            return has_input

    def getInputValue(self):
        """Return the branch defined by the input value."""
        return self._toFieldValue(self._getFormInput())

    def setRenderedValue(self, value):
        """This widget does not support setting the value."""
        pass

    def _renderLabel(self, text, index):
        """Render a label for the option with the specified index."""
        option_id = '%s.%s' % (self.name, index)
        return u'<label for="%s" style="font-weight: normal">%s</label>' % (
            option_id, text)

    def _renderBranchLabel(self, branch, index):
        """Render a label for the option based on a branch."""
        option_id = '%s.%s' % (self.name, index)

        # To aid usability there needs to be some text connected with the
        # radio buttons that is not a hyperlink in order to select the radio
        # button.  It was decided not to have the entire text as a link, but
        # instead to have a separate link to the branch details.
        text = '%s (<a href="%s">branch details</a>)' % (
            branch.displayname, canonical_url(branch))
        # If the branch is the development focus, say so.
        if branch == self.dev_focus:
            text = text + "&ndash; <em>development focus</em>"
        return u'<label for="%s" style="font-weight: normal">%s</label>' % (
            option_id, text)

    def renderItems(self, value):
        """Render the items for the selector."""
        field = self.context
        product = field.context
        if value == self._missing:
            value = field.missing_value

        items = []
        index = 0
        # Render each of the branches with the first selected.
        for index, term in enumerate(self.branch_selector_vocab):
            branch = term.value
            if index == 0:
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
        other_branch_text = "%s %s" % (
            self._renderLabel("Other:", index),
            self.other_branch_widget())
        other_branch_onclick = (
            "this.form['%s.target_branch'].focus()" % self.name)

        elem = renderElement(u'input',
                             value="other",
                             name=self.name,
                             id='%s.%s' % (self.name, index),
                             cssClass=self.cssClass,
                             type='radio',
                             onClick=other_branch_onclick)

        other_radio_button = self._joinButtonToMessageTemplate % (
            elem, other_branch_text)

        items.append(other_radio_button)

        return items

    def __call__(self):
        """Don't render the radio buttons if only one choice."""
        if len(self.branch_selector_vocab) == 0:
            return self.other_branch_widget()
        else:
            return LaunchpadRadioWidget.__call__(self)
