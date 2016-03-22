-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE GitRepository ADD COLUMN reviewer integer REFERENCES person;

COMMENT ON COLUMN GitRepository.reviewer IS 'The reviewer (person or) team are able to transition merge proposals targeted at the repository through the CODE_APPROVED state.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 61, 3);
