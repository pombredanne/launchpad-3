-- Copyright 2012 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

ALTER TABLE accesspolicy ADD COLUMN team integer;

ALTER TABLE accesspolicy ALTER COLUMN type DROP NOT NULL;

ALTER TABLE accesspolicy DROP CONSTRAINT has_target; 

ALTER TABLE accesspolicy ADD CONSTRAINT has_target
    CHECK ((((type is NOT NULL) AND (product IS NULL) <> (distribution IS NULL))
    OR (team IS NOT NULL AND type is NULL)));

ALTER TABLE ONLY accesspolicy
    ADD CONSTRAINT accesspolicy_team_fkey FOREIGN KEY (team) REFERENCES person(id);

CREATE UNIQUE INDEX accesspolicy__team__key ON accesspolicy USING btree (team) WHERE (team IS NOT NULL);

COMMENT ON TABLE AccessPolicy IS 'An access policy used to manage a project, distribution or private team''s artifacts.';
COMMENT ON COLUMN AccessPolicy.team IS 'The private team that this policy is used on.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 30, 1);
