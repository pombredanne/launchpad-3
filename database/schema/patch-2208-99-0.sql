-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

ALTER TABLE DistroSeriesDifference
    ADD COLUMN parent_series INTEGER NOT NULL
        CONSTRAINT distroseriesdifference__parentseries__fk REFERENCES distroseries;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
