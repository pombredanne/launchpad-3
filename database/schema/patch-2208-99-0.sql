-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE BugTrackerComponentGroup (
    id serial PRIMARY KEY,
    name text NOT NULL,
    bugtracker integer NOT NULL REFERENCES BugTracker
);

CREATE INDEX bugtrackercomponentgroup__bugtracker__idx
    ON BugTracker(id);

CREATE TABLE BugTrackerComponent (
    id serial PRIMARY KEY,
    name text NOT NULL,
    componentgroup integer NOT NULL REFERENCES BugTrackerComponentGroup,
    sourcepackage integer REFERENCES DistributionSourcePackage,

    -- There should be only one component per source package
    CONSTRAINT bugtrackercomponent__distributionsourcepackage__fk
        FOREIGN KEY(sourcepackage) REFERENCES DistributionSourcePackage
);

CREATE INDEX bugtrackercomponent__componentgroup__idx
    ON BugTrackerComponent(componentgroup);
CREATE INDEX bugtrackercomponent__distributionsourcepackage__idx
    ON BugTrackerComponent(sourcepackage);

INSERT INTO LaunchpadDatabaseRevision VALUES(2208, 99, 0);
