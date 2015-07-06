-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE WebHook (
    id serial PRIMARY KEY,
    git_repository integer REFERENCES GitRepository,
    registrant integer REFERENCES Person,
    date_created timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_last_modified timestamp without time zone DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    active boolean DEFAULT true NOT NULL,
    delivery_url text NOT NULL,
    secret text,
    json_data text NOT NULL,
    CHECK (git_repository IS NOT NULL) -- To be expanded to other targets later.
    );

CREATE TABLE WebHookJob (
    job integer PRIMARY KEY REFERENCES Job ON DELETE CASCADE NOT NULL,
    webhook integer REFERENCES WebHook NOT NULL,
    job_type integer NOT NULL,
    json_data text NOT NULL,
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 66, 0);
