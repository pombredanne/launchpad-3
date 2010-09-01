-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE BugTrackerComponentGroup (
    id serial PRIMARY KEY,
    name text NOT NULL,
    bug_tracker integer NOT NULL REFERENCES BugTracker
);

CREATE INDEX bugtrackercomponentgroup__bugtracker__idx
    ON BugTracker(id);

CREATE TABLE BugTrackerComponent (
    id serial PRIMARY KEY,
    name text NOT NULL,
    component_group integer NOT NULL REFERENCES BugTrackerComponentGroup,
    source_package integer REFERENCES DistributionSourcePackage,

    -- There should be only one component per source package
    CONSTRAINT bugtrackercomponent__distributionsourcepackage__fk
        FOREIGN KEY(source_package) REFERENCES DistributionSourcePackage
);

CREATE INDEX bugtrackercomponent__componentgroup__idx
    ON BugTrackerComponent(component_group);
CREATE INDEX bugtrackercomponent__distributionsourcepackage__idx
    ON BugTrackerComponent(source_package);

INSERT INTO LaunchpadDatabaseRevision VALUES(2208, 99, 0);
