
/*
  Allow bugs to have no shortdesc or description. This is based on feedback
  during the malone bof at mataro. Bugs will be created with an initial
  comment, rather than the summary / description.
*/

ALTER TABLE Bug ALTER COLUMN shortdesc DROP NOT NULL;
ALTER TABLE Bug ALTER COLUMN description DROP NOT NULL;

UPDATE LaunchpadDatabaseRevision SET major=6, minor=21, patch=0;


