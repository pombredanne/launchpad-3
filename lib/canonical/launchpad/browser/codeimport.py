# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser views for CodeImports."""

__metaclass__ = type

__all__ = [
    'CodeImportEditView',
    'CodeImportMachineView',
    'CodeImportNewView',
    'CodeImportSetView',
    'CodeImportView',
    ]


from BeautifulSoup import BeautifulSoup
from zope.app.form import CustomWidgetFactory
from zope.app.form.interfaces import IInputWidget
from zope.app.form.utility import setUpWidget
from zope.component import getUtility
from zope.formlib import form
from zope.schema import Choice, TextLine

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    BranchSubscriptionDiffSize, BranchSubscriptionNotificationLevel,
    branch_name_validator, CodeImportReviewStatus,
    CodeReviewNotificationLevel, IBranchSet, ICodeImport,
    ICodeImportMachineSet,  ICodeImportSet, ILaunchpadCelebrities,
    RevisionControlSystems)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadFormView, LaunchpadView)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.interfaces import NotFoundError
from canonical.launchpad.webapp.menu import structured
from canonical.widgets import LaunchpadDropdownWidget
from canonical.widgets.itemswidgets import LaunchpadRadioWidget
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


class CodeImportBaseView(LaunchpadFormView):
    """A base view for both new and edit code import views."""

    schema = ICodeImport

    custom_widget('cvs_root', StrippedTextWidget, displayWidth=50)
    custom_widget('cvs_module', StrippedTextWidget, displayWidth=20)
    custom_widget('svn_branch_url', URIWidget, displayWidth=50)

    @cachedproperty
    def _super_user(self):
        """Is the user an admin or member of vcs-imports?"""
        celebs = getUtility(ILaunchpadCelebrities)
        return (self.user.inTeam(celebs.admin) or
                self.user.inTeam(celebs.vcs_imports))

    def showOptionalMarker(self, field_name):
        """Don't show the optional marker for rcs locations."""
        # No field in either the new or edit view needs an optional marker,
        # so we can be simple here.
        return False

    def setSecondaryFieldError(self, field, error):
        """Set the field error only if there isn't an error already."""
        if self.getFieldError(field):
            # Leave this one as it is often required or a validator error.
            pass
        else:
            self.setFieldError(field, error)

    def _validateCVS(self, cvs_root, cvs_module, existing_import=None):
        """If the user has specified cvs, then we need to make
        sure that there isn't already an import with those values."""
        if cvs_root is None:
            self.setSecondaryFieldError(
                'cvs_root', 'Enter a CVS root.')
        if cvs_module is None:
            self.setSecondaryFieldError(
                'cvs_module', 'Enter a CVS module.')

        if cvs_root and cvs_module:
            code_import = getUtility(ICodeImportSet).getByCVSDetails(
                cvs_root, cvs_module)
            if (code_import is not None and
                code_import != existing_import):
                self.addError(structured("""
                    Those CVS details are already specified for
                    the imported branch <a href="%s">%s</a>.""",
                    canonical_url(code_import.branch),
                    code_import.branch.unique_name))

    def _validateSVN(self, svn_branch_url, existing_import=None):
        """If the user has specified a subversion url, we need
        to make sure that there isn't already an import with
        that url."""
        if svn_branch_url is None:
            self.setSecondaryFieldError(
                'svn_branch_url', 'Enter the URL of a Subversion branch.')
        else:
            code_import = getUtility(ICodeImportSet).getBySVNDetails(
                svn_branch_url)
            if (code_import is not None and
                code_import != existing_import):
                self.setFieldError(
                    'svn_branch_url',
                    structured("""
                    This Subversion branch URL is already specified for
                    the imported branch <a href="%s">%s</a>.""",
                    canonical_url(code_import.branch),
                    code_import.branch.unique_name))


class CodeImportNewView(CodeImportBaseView):
    """The view to request a new code import."""

    for_input = True
    label = 'Request a code import'
    field_names = [
        'product', 'rcs_type', 'svn_branch_url', 'cvs_root', 'cvs_module',
        ]

    custom_widget('rcs_type', LaunchpadRadioWidget)

    initial_values = {
        'rcs_type': RevisionControlSystems.SVN,
        'branch_name': 'trunk',
        }

    @property
    def cancel_url(self):
        """Cancel should take the user back to the root site."""
        return '/'

    def setUpFields(self):
        CodeImportBaseView.setUpFields(self)
        # Add in the field for the branch name.
        name_field = form.Fields(
            TextLine(
                __name__='branch_name',
                title=_('Branch Name'), required=True, description=_(
                    "This will be used in the branch URL to identify the "
                    "imported branch.  Examples: main, trunk."),
                constraint=branch_name_validator),
            render_context=self.render_context)
        self.form_fields = self.form_fields + name_field

    def setUpWidgets(self):
        CodeImportBaseView.setUpWidgets(self)

        # Extract the radio buttons from the rcs_type widget, so we can
        # display them separately in the form.
        soup = BeautifulSoup(self.widgets['rcs_type']())
        [cvs_button, svn_button, empty_marker] = soup.findAll('input')
        cvs_button['onclick'] = 'updateWidgets()'
        svn_button['onclick'] = 'updateWidgets()'
        # The following attributes are used only in the page template.
        self.rcs_type_cvs = str(cvs_button)
        self.rcs_type_svn = str(svn_button)
        self.rcs_type_emptymarker = str(empty_marker)

    def _create_import(self, data, status):
        """Create the code import."""
        return getUtility(ICodeImportSet).new(
            registrant=self.user,
            product=data['product'],
            branch_name=data['branch_name'],
            rcs_type=data['rcs_type'],
            svn_branch_url=data['svn_branch_url'],
            cvs_root=data['cvs_root'],
            cvs_module=data['cvs_module'],
            review_status=status)

    @action(_('Request Import'), name='request_import')
    def request_import_action(self, action, data):
        """Create the code_import, and subscribe the user to the branch."""
        code_import = self._create_import(data, None)

        # Subscribe the user.
        code_import.branch.subscribe(
            self.user,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.NODIFF,
            CodeReviewNotificationLevel.NOEMAIL)

        self.next_url = canonical_url(code_import.branch)

        self.request.response.addNotification("""
            New code import created. The code import operators
            have been notified and the request will be reviewed shortly.""")

    def _showApprove(self, ignored):
        """Is the user an admin or member of vcs-imports?"""
        return self._super_user

    @action(_('Create Approved Import'), name='approve',
            condition=_showApprove)
    def approve_action(self, action, data):
        """Create the code_import, and subscribe the user to the branch."""
        code_import = self._create_import(
            data, CodeImportReviewStatus.REVIEWED)

        # Don't subscribe the requester as they are an import operator.
        self.next_url = canonical_url(code_import.branch)

        self.request.response.addNotification(
            "New reviewed code import created.")

    def validate(self, data):
        """See `LaunchpadFormView`."""
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

        # Check for an existing branch owned by the vcs-imports
        # for the product and name specified.
        if data.get('product') and data.get('branch_name'):
            existing_branch = getUtility(IBranchSet).getBranch(
                getUtility(ILaunchpadCelebrities).vcs_imports,
                data['product'],
                data['branch_name'])
            if existing_branch is not None:
                self.setFieldError(
                    'branch_name',
                    structured("""
                    There is already an existing import for
                    <a href="%(product_url)s">%(product_name)s</a>
                    with the name of
                    <a href="%(branch_url)s">%(branch_name)s</a>.""",
                    product_url=canonical_url(existing_branch.product),
                    product_name=existing_branch.product.name,
                    branch_url=canonical_url(existing_branch),
                    branch_name=existing_branch.name))


class CodeImportEditView(CodeImportBaseView):
    """View for editing code imports.

    This view is registered against the branch, but edits the
    code import for that branch.  If the branch has no associated
    code import, then the result is a 404.  If the branch does have
    a code import, then the adapters property allows the form
    internals to do the associated mappings.
    """

    # Need this to render the context to prepopulate the form fields.
    # Added here as the base class isn't LaunchpadEditFormView.
    render_context = True
    field_names = ['svn_branch_url', 'cvs_root', 'cvs_module']

    def initialize(self):
        """Show a 404 if the branch has no code import."""
        self.code_import = self.context.code_import
        if self.code_import is None:
            raise NotFoundError
        # The next and cancel location is the branch details page.
        self.cancel_url = self.next_url = canonical_url(self.context)
        CodeImportBaseView.initialize(self)

    @property
    def adapters(self):
        """See `LaunchpadFormView`."""
        return {ICodeImport: self.code_import}

    def setUpFields(self):
        CodeImportBaseView.setUpFields(self)

        # If the import is a Subversion import, then omit the CVS
        # fields, and vice versa.
        if self.code_import.rcs_type == RevisionControlSystems.CVS:
            self.form_fields = self.form_fields.omit('svn_branch_url')
        elif self.code_import.rcs_type == RevisionControlSystems.SVN:
            self.form_fields = self.form_fields.omit('cvs_root', 'cvs_module')
        else:
            raise AssertionError('Unknown rcs_type for code import.')

    def _showButtonForStatus(self, status):
        """If the status is different, and the user is super, show button."""
        return self._super_user and self.code_import.review_status != status

    def _showApprove(self, ignored):
        """Show the Approve button if the import is not reviewed."""
        return self._showButtonForStatus(CodeImportReviewStatus.REVIEWED)

    def _showInvalidate(self, ignored):
        """Show the Approve button if the import is not invalid."""
        return self._showButtonForStatus(CodeImportReviewStatus.INVALID)

    def _showSuspend(self, ignored):
        """Show the Suspend button if the import is not suspended."""
        return self._showButtonForStatus(CodeImportReviewStatus.SUSPENDED)

    @action(_('Update'), name='update')
    def update_action(self, action, data):
        """Update the details."""
        self.code_import.updateFromData(data, self.user)

    @action(_('Approve'), name='approve', condition=_showApprove)
    def approve_action(self, action, data):
        """Approve the import."""
        self.code_import.approve(data, self.user)
        self.request.response.addNotification(
            'The code import has been approved.')

    @action(_('Mark Invalid'), name='invalidate', condition=_showInvalidate)
    def invalidate_action(self, action, data):
        """Invalidate the import."""
        self.code_import.invalidate(data, self.user)
        self.request.response.addNotification(
            'The code import has been set as invalid.')

    @action(_('Suspend'), name='suspend', condition=_showSuspend)
    def suspend_action(self, action, data):
        """Suspend the import."""
        self.code_import.suspend(data, self.user)
        self.request.response.addNotification(
            'The code import has been suspended.')

    def validate(self, data):
        """See `LaunchpadFormView`."""
        # A simple else clause is sufficient here as the initialize would
        # have barfed if there was a different type (other than CVS or SVN).
        if self.code_import.rcs_type == RevisionControlSystems.CVS:
            self._validateCVS(
                data.get('cvs_root'), data.get('cvs_module'),
                self.code_import)
        elif self.code_import.rcs_type == RevisionControlSystems.SVN:
            self._validateSVN(
                data.get('svn_branch_url'), self.code_import)
        else:
            raise AssertionError('Unknown rcs_type for code import.')


class CodeImportMachineView(LaunchpadView):
    """The view for the page that shows all the import machines."""

    __used_for__ = ICodeImportSet

    label = "Import machines for Launchpad"

    @property
    def machines(self):
        """Get the machines, sorted alphabetically by hostname."""
        return getUtility(ICodeImportMachineSet).getAll()
