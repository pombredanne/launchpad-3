SET client_min_messages=ERROR;

CREATE TABLE usertouseremail (
    id integer NOT NULL,
    sender_id integer NOT NULL,
    recipient_id integer NOT NULL,
    date_sent timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    subject text NOT NULL,
    message_id text NOT NULL
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99,0);
