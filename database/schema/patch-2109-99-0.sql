SET client_min_messages=ERROR;

CREATE TABLE specificationmessage (
    id integer NOT NULL,
    specification integer NOT NULL,
    message integer NOT NULL,
    visible boolean DEFAULT true NOT NULL
);

CREATE SEQUENCE specificationmessage_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;

ALTER SEQUENCE specificationmessage_id_seq OWNED BY specificationmessage.id;

ALTER TABLE specificationmessage ALTER COLUMN id SET DEFAULT nextval('specificationmessage_id_seq'::regclass);

ALTER TABLE ONLY specificationmessage
    ADD CONSTRAINT specificationmessage_specification_id_key UNIQUE (specification, id);

ALTER TABLE ONLY specificationmessage
    ADD CONSTRAINT specificationmessage_message_key UNIQUE (message);

ALTER TABLE ONLY specificationmessage
    ADD CONSTRAINT specificationmessage_pkey PRIMARY KEY (id);

ALTER TABLE ONLY specificationmessage
    ADD CONSTRAINT specificationmessage_specification_fkey FOREIGN KEY (specification) REFERENCES specification(id);

ALTER TABLE ONLY specificationmessage
    ADD CONSTRAINT specificationmessage_message_fkey FOREIGN KEY (message) REFERENCES message(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 99, 0);
