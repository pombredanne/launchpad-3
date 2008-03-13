# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for CodeImports."""

__metaclass__ = type

__all__ = [
    'CodeImportSetView',
    'CodeImportNewView',
    'CodeImportView',
    ]


from BeautifulSoup import BeautifulSoup
from zope.app.form import CustomWidgetFactory
from zope.app.form.interfaces import IInputWidget
from zope.app.form.utility import setUpWidget
from zope.component import getUtility
from zope.formlib import form
from zope.schema import Choice, TextLine

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    BranchSubscriptionDiffSize, BranchSubscriptionNotificationLevel,
    branch_name_validator, CodeImportReviewStatus, ICodeImport, ICodeImportSet,
    ILaunchpadCelebrities, ILaunchpadRoot,
    RevisionControlSystems)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadFormView, LaunchpadView)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.widgets import LaunchpadDropdownWidget
from canonical.widgets.itemswidgets import (
    LaunchpadRadioWidget, LaunchpadRadioWidgetWithDescription)
from canonical.widgets.textwidgets import StrippedTextWidget, URIWidget


class ReviewStatusDropdownWidget(LaunchpadDropdownWidget):
    """A <select> widget with a more appropriate 'no value' message.

    By default `LaunchpadDropdownWidget` displays 'no value' when the
    associated value is None or not supplied, which is not what we want on
    this page.
    """
    _messageNoValue = _('Any')


class CodeImportSetView(LaunchpadView):
    """The default view for `ICodeImportSet`.

    We present the CodeImportSet as a list of all imports.
    """

    def initialize(self):
        """See `LaunchpadView.initialize`."""
        status_field = Choice(
            __name__='status', title=_("Review Status"),
            vocabulary=CodeImportReviewStatus, required=False)
        self.status_widget = CustomWidgetFactory(ReviewStatusDropdownWidget)
        setUpWidget(self, 'status',  status_field, IInputWidget)

        # status should be None if either (a) there were no query arguments
        # supplied, i.e. the user browsed directly to this page (this is when
        # hasValidInput returns False) or (b) the user chose 'Any' in the
        # status widget (this is when hasValidInput returns True but
        # getInputValue returns None).
        status = None
        if self.status_widget.hasValidInput():
            status = self.status_widget.getInputValue()

        if status is not None:
            imports = self.context.search(review_status=status)
        else:
            imports = self.context.getAll()

        self.batchnav = BatchNavigator(imports, self.request)


class CodeImportView(LaunchpadView):
    """The default view for `ICodeImport`.

    We present the CodeImport as a simple page listing all the details of the
    import such as associated product and branch, who requested the import,
    and so on.
    """

    def initialize(self):
        """See `LaunchpadView.initialize`."""
        self.title = "Code Import for %s" % (self.context.product.name,)


class CodeImportNewView(LaunchpadFormView):
    """The view to request a new code import."""

    for_input = True
    label = 'Request a code import'
    schema = ICodeImport
    field_names = [
        'product', 'rcs_type', 'svn_branch_url', 'cvs_root', 'cvs_module',
        'review_status'
        ]

    custom_widget('rcs_type', LaunchpadRadioWidget)
    custom_widget('cvs_root', StrippedTextWidget, displayWidth=50)
    custom_widget('cvs_module', StrippedTextWidget, displayWidth=20)
    custom_widget('svn_branch_url', URIWidget, displayWidth=50)
    custom_widget('review_status', LaunchpadRadioWidgetWithDescription)

    initial_values = {'rcs_type': RevisionControlSystems.SVN}

    def showOptionalMarker(self, field_name):
        """Don't show the optional marker for rcs locations."""
        if field_name in ('cvs_root', 'cvs_module', 'svn_branch_url'):
            return False
        else:
            return LaunchpadFormView.showOptionalMarker(self, field_name)

    def setUpFields(self):
        LaunchpadFormView.setUpFields(self)
        # Add in the field for the branch name.
        name_field = form.Fields(
            TextLine(
                __name__='branch_name',
                title=_('Name'), required=True, description=_(
                    "Keep very short, unique, and descriptive, because it "
                    "will be used in URLs. "
                    "Examples: main, trunk."),
                constraint=branch_name_validator),
            render_context=self.render_context)

        self.form_fields = self.form_fields + name_field
        if not self.show_review_status:
            # Omit the field so it doesn't attempt to validate it.
            self.form_fields = self.form_fields.omit('review_status')

    @property
    def show_review_status(self):
        if self.user is None:
            return False
        celebs = getUtility(ILaunchpadCelebrities)
        return (self.user.inTeam(celebs.vcs_imports) or
                self.user.inTeam(celebs.admin))

    def setUpWidgets(self):
        LaunchpadFormView.setUpWidgets(self)

        # Extract the radio buttons from the rcstype widget, so we can
        # display them separately in the form.
        soup = BeautifulSoup(self.widgets['rcs_type']())
        [cvs_button, svn_button, empty_marker] = soup.findAll('input')
        cvs_button['onclick'] = 'updateWidgets()'
        svn_button['onclick'] = 'updateWidgets()'
        # These are just only in the page template.
        self.rcs_type_cvs = str(cvs_button)
        self.rcs_type_svn = str(svn_button)
        self.rcs_type_emptymarker = str(empty_marker)

    @action(_('Continue'), name='continue')
    def continue_action(self, action, data):
        """Create the code_import, and subscribe the user to the branch."""
        code_import = getUtility(ICodeImportSet).new(
            registrant=self.user,
            product=data['product'],
            branch_name=data['branch_name'],
            rcs_type=data['rcs_type'],
            svn_branch_url=data['svn_branch_url'],
            cvs_root=data['cvs_root'],
            cvs_module=data['cvs_module'],
            review_status=data.get('review_status'))

        code_import.branch.subscribe(
            self.user,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.NODIFF)

        self.next_url = canonical_url(code_import.branch)

    @action('Cancel', name='cancel', validator='validate_cancel')
    def cancel_action(self, action, data):
        """Do nothing and go back to the code rootsite."""
        self.next_url = canonical_url(ILaunchpadRoot, rootsite='code')

    def _validateCVS(self, cvs_root, cvs_module):
        # Make sure there is an error set for these fields if they
        # are unset.
        if not (cvs_root or self.getFieldError('cvs_root')):
            self.setFieldError('cvs_root',
                               'Enter a CVS root.')
        if not (cvs_module or self.getFieldError('cvs_module')):
            self.setFieldError('cvs_module',
                               'Enter a CVS module.')

        if cvs_root and cvs_module:
            code_import = getUtility(ICodeImportSet).getByCVSDetails(
                cvs_root, cvs_module)

            if code_import is not None:
                self.addError(
                    "Those CVS details are already specified for"
                    " the imported branch <a href=\"%s\">%s</a>."
                    % (canonical_url(code_import.branch),
                       code_import.branch.uniquename))

    def _validateSVN(self, svn_branch_url):
        if not (svn_branch_url or self.getFieldError('svn_branch_url')):
            self.setFieldError('svn_branch_url',
                               "Enter the URL of a Subversion branch.")
        if svn_branch_url:
            code_import = getUtility(ICodeImportSet).getBySVNDetails(
                svn_branch_url)
            if code_import is not None:
                self.setFieldError(
                    'svn_branch_url',
                    "This Subversion branch URL is already specified for"
                    " the imported branch <a href=\"%s\">%s</a>."
                    % (canonical_url(code_import.branch),
                       code_import.branch.uniquename))

    def validate(self, data):
        # If the user has specified a subversion url, we need
        # to make sure that there isn't already an import with
        # that url.

        # If the user has specified cvs, then we need to make
        # sure that there isn't already an import with those
        # values.
        rcs_type = data['rcs_type']

        # Make sure fields for unselected revision control systems
        # are blanked out:
        if rcs_type == RevisionControlSystems.CVS:
            data['svn_repository'] = None
            self._validateCVS(data.get('cvs_root'), data.get('cvs_module'))
        elif rcs_type == RevisionControlSystems.SVN:
            data['cvs_root'] = None
            data['cvs_module'] = None
            self._validateSVN(data.get('svn_branch_url'))
        else:
            raise AssertionError('Unknown revision control type.')
