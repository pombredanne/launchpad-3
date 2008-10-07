SET client_min_messages=ERROR;

CREATE TABLE usertouseremail (
    id integer NOT NULL,
    sender integer NOT NULL,
    recipient integer NOT NULL,
    date_sent timestamp without time zone DEFAULT timezone('UTC'::text, now()) NOT NULL,
    subject text NOT NULL,
    message_id text NOT NULL
    );

ALTER TABLE ONLY usertouseremail
    ADD CONSTRAINT usertouseremail_pkey PRIMARY KEY (id);

CREATE SEQUENCE usertouseremail_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE usertouseremail_id_seq OWNED BY usertouseremail.id;

ALTER TABLE usertouseremail
ALTER COLUMN id
SET DEFAULT nextval('usertouseremail_id_seq'::regclass);

ALTER TABLE ONLY usertouseremail
ADD CONSTRAINT usertouseremail_sender_fkey
FOREIGN KEY (sender_id) REFERENCES person(id);

ALTER TABLE ONLY usertouseremail
ADD CONSTRAINT usertouseremail_recipient_fkey
FOREIGN KEY (recipient_id) REFERENCES person(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99,0);
