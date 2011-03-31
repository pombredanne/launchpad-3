-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- A table to store subscription mutes in.

CREATE TABLE BugSubscriptionFilterMute (
    id serial PRIMARY KEY,
    person integer REFERENCES Person(id) NOT NULL,
    filter integer REFERENCES BugSubscriptionFilter(id) 
        ON DELETE CASCADE NOT NULL,
    date_created timestamp without time zone
        DEFAULT timezone('UTC'::text, now())
);

CREATE INDEX bugsubscriptionfiltermute__bug_subscription_filter
    ON BugSubscriptionFilterMute(filter);
CREATE INDEX bugsubscriptionfiltermute__person
    ON BugSubscriptionFilterMute(person);

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);
