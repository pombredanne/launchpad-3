Put scripts here that should be run at completion of the publish-ftpmaster
script.  They will be executed through the run-parts command, in alphabetical
order.

The scripts' filenames must consist entirely of ASCII letters (both upper and
lower case allowed), digits, underscores, and hyphens.  All other files,
including this text file, are ignored.

Publication happens in two passes: the first, expedited pass processes only
security updates.  The second pass processes all packages.  The scripts in
this directory will be run once for each pass, with the variable
SECURITY_UPLOAD_ONLY set to indicate which pass is in progress; see below.

The following variables will be set for the script:

ARCHIVEROOTS - the list of root directories for the distribution's archives.
(e.g. /foo/ubuntu-archive/ubuntu/ /foo/ubuntu-archive/ubuntu-partner/ )

PRIMARY_ARCHIVEROOT - the root directory for the distribution's main archive.
(e.g. /srv/launchpad.net/ubuntu-archive/ubuntu/ )

SECURITY_UPLOAD_ONLY - "yes" during the security pass, or "no" otherwise.
