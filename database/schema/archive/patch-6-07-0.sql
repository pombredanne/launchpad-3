
/*
  We need a displayname and summary on a Distribution. The "summary" column
  is what I should have called shortdesc a long time ago, so I'll start
  using it here, and will big-bang the change after all the first-round
  demos are done.
*/

SET client_min_messages=ERROR;

ALTER TABLE Distribution ADD COLUMN displayname text;
UPDATE Distribution SET displayname=name;
ALTER TABLE Distribution ALTER COLUMN displayname SET NOT NULL;

COMMENT ON COLUMN Distribution.displayname IS 'A short, well-capitalised
name for this distribution that is not required to be unique but in almost
all cases would be so.';

ALTER TABLE Distribution ADD COLUMN summary text;
UPDATE Distribution SET summary=substring(description from 1 for 240);
ALTER TABLE Distribution ALTER COLUMN summary SET NOT NULL;

COMMENT ON COLUMN Distribution.summary IS 'A single paragraph that
summarises the highlights of this distribution. It should be no longer than
240 characters, although this is not enforced in the database.';

COMMENT ON COLUMN Distribution.domainname IS 'The top domain of the
distribution. For example, for Gentoo this would be gentoo.org. This allows
us to know, for example, that a request sent to "launchpad.gentoo.org"
belongs to the Gentoo distribution, so we can present a simplified Launchpad
for Gentoo users.';


ALTER TABLE DistroRelease ADD COLUMN displayname text;
UPDATE DistroRelease SET displayname=name;
ALTER TABLE DistroRelease ALTER COLUMN displayname SET NOT NULL;

UPDATE LaunchpadDatabaseRevision SET major=6, minor=7, patch=0;

