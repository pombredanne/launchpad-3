-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Renaming owner to registrant for DistroSeries

-- Rename owner into registrant.
ALTER TABLE distroseries 
    RENAME COLUMN owner TO registrant;

-- 'Rename' constraint.
ALTER TABLE distroseries 
    ADD CONSTRAINT distroseries__registrant__fk 
    FOREIGN KEY (registrant) REFERENCES Person(id);
ALTER TABLE distroseries
    DROP CONSTRAINT distroseries__owner__fk;


INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
