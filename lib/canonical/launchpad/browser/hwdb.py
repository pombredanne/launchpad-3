# Copyright 2007 Canonical Ltd

__metaclass__ = type

__all__ = [
    'HWDBFingerprintSetView',
    'HWDBSubmissionSetNavigation',
    'HWDBPersonSubmissionsView',
    'HWDBUploadView']

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher

from canonical.launchpad.interfaces import (
    HWSubmissionInvalidEmailAddress, IDistributionSet, IHWDBApplication,
    IHWSubmissionForm, IHWSubmissionSet, IHWSystemFingerprintSet, 
    NotFoundError)
from canonical.launchpad.webapp import (
    action, LaunchpadView, LaunchpadFormView, Navigation, stepthrough)
from canonical.launchpad.webapp.batching import BatchNavigator


class HWDBUploadView(LaunchpadFormView):
    """View class for hardware database submissions."""

    schema = IHWSubmissionForm

    @action(u'Upload', name='upload')
    def upload_action(self, action, data):
        """Create a record in the HWSubmission table."""
        distributionset = getUtility(IDistributionSet)
        distribution = distributionset.getByName(data['distribution'])
        if distribution is not None:
            release = data['distrorelease']
            architecture = data['architecture']
            try:
                distroseries = distribution.getSeries(release)
                distroarchseries = distroseries[architecture]
            except NotFoundError:
                distroarchseries = None
        else:
            distroarchseries = None

        fingerprintset = getUtility(IHWSystemFingerprintSet)
        fingerprint = fingerprintset.getByName(data['system'])
        if fingerprint is None:
            fingerprint = fingerprintset.createFingerprint(data['system'])

        submitted_data = data['submission_data']
        filesize = len(data['submission_data'])
        submission_file = self.request.form[
            self.widgets['submission_data'].name]
        submission_file.seek(0)
        # convert a filename with "path elements" to a regular filename
        filename = submission_file.filename.replace('/', '-')

        hw_submissionset = getUtility(IHWSubmissionSet)
        try:
            hw_submissionset.createSubmission(
                date_created=data['date_created'],
                format=data['format'],
                private=data['private'],
                contactable=data['contactable'],
                submission_key=data['submission_id'],
                emailaddress=data['emailaddress'],
                distroarchseries=distroarchseries,
                raw_submission=submission_file,
                filename=filename,
                filesize=filesize,
                system_fingerprint=data['system'])
        except HWSubmissionInvalidEmailAddress:
            self.addCustomHeader(
                'Emailaddress',
                "Error - %s isn't a valid email address" % data['emailaddress'])
            self.request.response.addErrorNotification(
                "Error: %(address)s email address is invalid",
                address = data['emailaddress'])
            return

        self.addCustomHeader('', 'OK data stored')
        self.request.response.addNotification(
            "Thank you for your submission.")

    def render(self):
        """See ILaunchpadFormView."""
        if self.errors:
            self.setHeadersForHWDBClient()
        return LaunchpadFormView.render(self)

    def setHeadersForHWDBClient(self):
        """Add headers that help the HWDB client detect a successful upload.

        An upload is normally not made by a regular web browser, but by the
        HWDB client. In order to allow the client to easily detect a
        successful as well as an failed request, add some HTTP headers
        to the response.
        """
        response = self.request.response
        for field in self.form_fields:
            field_name = field.__name__
            error = self.getWidgetError(field_name)
            if error:
                self.addCustomHeader(field_name, u'Error - %s' % error)

    def addCustomHeader(self, field_name, value):
        if field_name:
            self.request.response.setHeader(
                u'X-Launchpad-HWDB-Submission-%s' % field_name, value)
        else:
            self.request.response.setHeader(
                u'X-Launchpad-HWDB-Submission', value)
        

class HWDBPersonSubmissionsView(LaunchpadView):
    """View class for preseting HWDB submissions by a person."""

    def getAllBatched(self):
        """Return the list of HWDB submissions made by this person."""
        hw_submissionset = getUtility(IHWSubmissionSet)
        submissions = hw_submissionset.getByOwner(self.context, self.user)
        return BatchNavigator(submissions, self.request)

    def userIsOwner(self):
        """Return true, if self.context == self.user"""
        return self.context == self.user


class HWDBSubmissionSetNavigation(Navigation):
    """Navigation class for HWDBSubmissionSet."""

    usedfor = IHWDBApplication

    @stepthrough('+hwdb-fingerprint')
    def traverse_hwdb_fingerprint(self, name):
        return HWDBFingerprintSetView(self.context, self.request, name)


class HWDBFingerprintSetView(LaunchpadView):
    """View class for lists of HWDB submissions for a system fingerprint."""

    implements(IBrowserPublisher)

    template = ViewPageTemplateFile(
        '../templates/hwdb-fingerprint-submissions.pt')
    
    def __init__(self, context,  request, system_name):
        LaunchpadView.__init__(self, context, request)
        self.system_name = system_name

    def getAllBatched(self):
        """A BatchNavigator instance with the submissions."""
        submissions = getUtility(IHWSubmissionSet).getByFingerprintName(
            self.system_name, self.user)
        return BatchNavigator(submissions, self.request)

    def browserDefault(self, request):
        """See `IBrowserPublisher`."""
        return self, ()

    def showOwner(self, submission):
        """Check if the owner can be shown in the list.
        """
        return (submission.owner is not None
                and (submission.contactable
                     or (submission.owner == self.user)))
