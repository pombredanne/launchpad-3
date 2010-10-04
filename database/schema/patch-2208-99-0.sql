-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE BugTrackerComponent
    ADD COLUMN distribution integer REFERENCES Distribution;

ALTER TABLE BugTrackerComponent
    ADD COLUMN source_package_name integer REFERENCES SourcePackageName;

ALTER TABLE BugTrackerComponent
    DROP CONSTRAINT bugtrackercomponent__distro_source_package__key;

ALTER TABLE BugTrackerComponent
    DROP COLUMN distro_source_package;


INSERT INTO LaunchpadDatabaseRevision VALUES(2208, 99, 0);
