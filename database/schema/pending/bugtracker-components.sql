-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE BugTrackerComponent (
    id serial PRIMARY KEY,
    name text NOT NULL,
    componentgroup NOT NULL REFERENCES BugTrackerComponentGroup,
    distrosourcepackage integer REFERENCES DistroSourcePackage,

    -- There should be only one BugTrackerComponent per DistroSourcePackage
    CONSTRAINT bugtrackercomponent__distrosourcepackage__fk
        FOREIGN KEY(distrosourcepackage) REFERENCES DistroSourcePackage
);

CREATE TABLE BugTrackerComponentGroup (
    id serial PRIMARY KEY,
    name text NOT NULL,
    bugtracker integer NOT NULL REFERENCES BugTracker
);


-- Indexes required for person merge and looking up affiliations for a person
CREATE INDEX bugtrackercomponent__distrosourcepackage__idx
    ON BugTrackerComponent(distrosourcepackage);
