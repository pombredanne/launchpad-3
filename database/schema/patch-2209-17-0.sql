-- Copyright 2012 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE sharingjob (
    id integer NOT NULL,
    job integer NOT NULL,
    product integer,
    distro integer,
    grantee integer,
    job_type integer NOT NULL,
    json_data text
);


COMMENT ON TABLE sharingjob IS 'Contains references to jobs that are executed for sharing.';

COMMENT ON COLUMN sharingjob.job IS 'A reference to a row in the Job table that has all the common job details.';

COMMENT ON COLUMN sharingjob.product IS 'The product that this job is for.';

COMMENT ON COLUMN sharingjob.distro IS 'The distro that this job is for.';

COMMENT ON COLUMN sharingjob.grantee IS 'The grantee that this job is for.';

COMMENT ON COLUMN sharingjob.job_type IS 'The type of job, like remove subscriptions, email users.';

COMMENT ON COLUMN sharingjob.json_data IS 'Data that is specific to the type of job.';


CREATE SEQUENCE sharingjob_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER SEQUENCE sharingjob_id_seq OWNED BY sharingjob.id;

ALTER TABLE sharingjob ALTER COLUMN id SET DEFAULT nextval('sharingjob_id_seq'::regclass);

ALTER TABLE ONLY sharingjob
    ADD CONSTRAINT sharingjob_job_key UNIQUE (job);

ALTER TABLE ONLY sharingjob
    ADD CONSTRAINT sharingjob_pkey PRIMARY KEY (id);

ALTER TABLE ONLY sharingjob
    ADD CONSTRAINT sharingjob_job_fkey FOREIGN KEY (job) REFERENCES job(id) ON DELETE CASCADE;


INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 17, 0);
