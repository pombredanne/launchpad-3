SET client_min_messages=ERROR;

/*
  Renames the table Membership to TeamMembership, to be consistent with our
  TeamParticipation table. Fixes Malone#96.
*/

ALTER TABLE Membership RENAME TO TeamMembership;

ALTER TABLE membership_id_seq RENAME TO teammembership_id_seq;
ALTER TABLE membership_pkey RENAME TO teammembership_pkey;
ALTER TABLE membership_person_key RENAME TO teammembership_person_pkey;

ALTER TABLE TeamMembership
    ALTER COLUMN id SET DEFAULT nextval('teammembership_id_seq');

UPDATE LaunchpadDatabaseRevision SET major=6, minor=32, patch=0;

