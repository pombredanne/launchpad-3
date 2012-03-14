SET client_min_messages=ERROR;

CREATE TABLE productjob (
    id SERIAL PRIMARY KEY,
    job integer NOT NULL,
    job_type integer NOT NULL,
    product integer NOT NULL REFERENCES product,
    json_data text
);


COMMENT ON TABLE productjob IS
'Contains references to jobs for updating projects and sendd notifications.';

COMMENT ON COLUMN productjob.job IS
'A reference to a row in the Job table that has all the common job details.';

COMMENT ON COLUMN productjob.job_type IS
'The type of job, like 30-day-renewal.';

COMMENT ON COLUMN productjob.product IS
'The product that is being updated or the maintainers needs notification.';

COMMENT ON COLUMN productjob.json_data IS
'Data that is specific to the job type, such as text for notifications.';

-- Queries will search for recent jobs of a specific type.
-- Maybe this is unproductive because there may never be more than 20 types.
CREATE INDEX productjob__job_type_idx
    ON productjob USING btree (job_type);


INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 15, 1);
