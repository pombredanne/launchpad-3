# Copyright 2007 Canonical Ltd

__metaclass__ = type

__all__ = [
    'HWDBPersonSubmissionsView',
    'HWDBUploadView']

from datetime import datetime
from StringIO import StringIO

from zope.component import getUtility

from canonical.launchpad.interfaces import (IDistributionSet,
    IHWDBSubmissionForm, IHWDBSubmissionSet, IHWDBSystemFingerprintSet,
    NotFoundError)
from canonical.launchpad.webapp import (
    action, LaunchpadView, LaunchpadFormView)


class HWDBUploadView(LaunchpadFormView):
    """View class for hardware database submissions."""

    schema = IHWDBSubmissionForm

    @action(u'Upload', name='upload')
    def upload_action(self, action, data):
        """Create a record in the HWDBSubmission table."""
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

        fingerprintset = getUtility(IHWDBSystemFingerprintSet)
        fingerprint = fingerprintset.getByName(data['system'])
        if fingerprint is None:
            fingerprint = fingerprintset.createFingerprint(data['system'])

        submitted_data = data['submission_data']
        filesize = len(data['submission_data'])
        file_ = self.request.form[self.widgets['submission_data'].name]
        file_.seek(0)
        # xxxxxxxxxx testen!
        filename = file_.filename.replace('/', '-')

        #xxx print "xxxxx errors", self.errors
        #xxx self.errors.append('asdf') #xxxxxxxxx
        hwdb_submissionset = getUtility(IHWDBSubmissionSet)
        hwdb_submissionset.createSubmission(
            date_created=data['date_created'],
            format=data['format'],
            private=data['private'],
            contactable=data['contactable'],
            livecd=data['livecd'],
            submission_id=data['submission_id'],
            emailaddress=data['emailaddress'],
            distroarchseries=distroarchseries,
            raw_submission=file_,
            filename=filename,
            filesize=filesize,
            system=data['system'])
        self.request.response.addHeader('X-lphwdb', 'OK data stored')
        self.request.response.addNotification(
            "Thank you for your submission.")

    def render(self):
        """Add headers that help the HWDB client detect a successful upload.

        An upload is normally not made by a regular web browser, but by the
        HWDB client. In order to allow the client to easily detect a
        successful as well as an failed request, add some HTTP headers
        to the response.
        """
        if self.errors:
            response = self.request.response
            for field in self.form_fields:
                field_name = field.__name__
                error = self.getWidgetError(field_name)
                if error:
                    response.setHeader(
                    u'X-lphwdb-%s' % field_name, u'Error - %s' % error)
        res = LaunchpadFormView.render(self)
        return res

class HWDBPersonSubmissionsView(LaunchpadView):
    """View class for preseting HWDB submissions by a person."""

    def getSubmissions(self):
        """Return the list of HWDB submissions made by this user"""
        hwdb_submissionset = getUtility(IHWDBSubmissionSet)
        return hwdb_submissionset.getByOwner(self.context, self.user)

    def userIsOwner(self):
        """Return true, if self.context == self.user"""
        return self.context == self.user
