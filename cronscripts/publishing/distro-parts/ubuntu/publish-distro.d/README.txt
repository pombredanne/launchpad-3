Put scripts here that should be run after publish-ftpmaster executes
publish-distro.  They will be executed through the run-parts command, in
alphabetical order.

The scripts' filenames must consist entirely of ASCII letters (both upper and
lower case allowed), digits, underscores, and hyphens.  All other files,
including this text file, are ignored.

Scripts in this directory will be run separately for each distro archive,
possibly twice because publication happens in two passes: an expedited one for
just the security uploads and then a second, slower pass for all packages.

Some variables will be set before each script is run:

ARCHIVEROOT - the archive's root directory
(e.g. /srv/launchpad.net/ubuntu-archive/ubuntu/ )

DISTSROOT - a working copy of the archive's dists root directory
(e.g. /srv/launchpad.net/ubuntu-archive/ubuntu/dists.new )

OVERRIDEROOT - the archive's overrides root directory (primary archive only)
(e.g. /srv/launchpad.net/ubuntu-overrides, or the empty string for partner)

The script's PATH will be extended with the Launchpad source tree's
cronscripts/publishing directory.
