-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE builder
    ADD COLUMN clean_status integer NOT NULL DEFAULT 1,
    ADD COLUMN vm_reset_protocol integer,
    ADD COLUMN date_clean_status_changed timestamp without time zone
        NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 57, 0);
