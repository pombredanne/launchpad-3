-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE Webhook (
    id serial PRIMARY KEY,
    registrant integer REFERENCES Person NOT NULL,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    date_last_modified timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    active boolean DEFAULT true NOT NULL,
    delivery_url text NOT NULL,
    secret text,
    json_data text NOT NULL,
    git_repository integer REFERENCES GitRepository,
    CHECK (git_repository IS NOT NULL) -- To be expanded to other targets.
    );

CREATE TABLE WebhookJob (
    job integer PRIMARY KEY REFERENCES Job ON DELETE CASCADE NOT NULL,
    webhook integer REFERENCES Webhook NOT NULL,
    job_type integer NOT NULL,
    json_data text NOT NULL
    );

CREATE INDEX webhook__git_repository__id__idx
    ON webhook(git_repository, id) WHERE git_repository IS NOT NULL;

CREATE INDEX webhookjob__webhook__job_type__job__idx
    ON webhookjob(webhook, job_type, job);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 66, 0);
