# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Rejection and acceptance message templates for the uploader etc."""

__all__ = [
    'rejection_template',
    'new_template',
    'accepted_template',
    'announce_template'
    ]

rejection_template = """From: %(SENDER)s
To: %(RECIPIENT)s
Bcc: %(DEFAULT_RECIPIENT)s
Subject: %(CHANGES)s rejected
X-Katie: Launchpad actually

Rejected:
%(SUMMARY)s

%(CHANGESFILE)s

===

If you don't understand why your files were rejected, or if the
override file requires editing, reply to this email.

-- 
You are receiving this email because you are the uploader, maintainer or
signer of the above package.
"""

new_template = """From: %(SENDER)s
To: %(RECIPIENT)s
Bcc: %(DEFAULT_RECIPIENT)s
Subject: %(CHANGES)s is NEW
X-Katie: Launchpad actually

%(SUMMARY)s

%(CHANGESFILE)s

Your package contains new components which requires manual editing of
the override file.  It is ok otherwise, so please be patient.  New
packages are usually added to the overrides about once a week.

You may have gotten the distroseries wrong.  If so, you may get warnings
above if files already exist in other distroseries.

-- 
You are receiving this email because you are the uploader, maintainer or
signer of the above package.
"""

accepted_template="""From: %(SENDER)s
To: %(RECIPIENT)s
Bcc: %(DEFAULT_RECIPIENT)s
Subject: %(STATUS)s %(SOURCE)s %(VERSION)s (%(ARCH)s)
X-Katie: Launchpad actually

%(STATUS)s:
%(SUMMARY)s

%(CHANGESFILE)s

==

Announcing to %(ANNOUNCE)s

Thank you for your contribution to %(DISTRO)s.

-- 
You are receiving this email because you are the uploader, maintainer or
signer of the above package.
"""

# The Debian PTS offers a way of notifying subscribers of when
# derivative packages are uploaded. For instance, we carbon copy
# firefox_derivatives@packages.qa.debian.org when uploading firefox.
announce_template="""From: %(MAINTAINERFROM)s
To: %(ANNOUNCE)s
Bcc: %(DEFAULT_RECIPIENT)s, %(SOURCE)s_derivatives@packages.qa.debian.org
Subject: Accepted %(SOURCE)s %(VERSION)s (%(ARCH)s)
X-Katie: Launchpad actually

Accepted:
%(SUMMARY)s

%(CHANGESFILE)s

"""
