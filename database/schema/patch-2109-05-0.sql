-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages = ERROR;

CREATE TABLE UserToUserEmail (
    id SERIAL PRIMARY KEY,
    sender integer NOT NULL
        CONSTRAINT usertouseremail__sender__fk REFERENCES Person,
    recipient integer NOT NULL
        CONSTRAINT usertouseremail__recipient__fk REFERENCES Person,
    date_sent timestamp without time zone NOT NULL
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    subject text NOT NULL,
    message_id text NOT NULL
    );

-- Index for person merge and checking recent outgoings for throttling.
CREATE INDEX usertouseremail__sender__date_sent__idx
    ON UserToUserEmail(sender, date_sent);

-- Index for person merge.
CREATE INDEX usertouseremail__recipient__idx
    ON UserToUserEmail(recipient);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 5, 0);
