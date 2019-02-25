-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE GitRepository ADD COLUMN description text;

COMMENT ON COLUMN GitRepository.description IS 'A short description of this repository.';

ALTER TABLE GitRef ADD COLUMN object_type integer NOT NULL;
ALTER TABLE GitRef ADD COLUMN author integer REFERENCES revisionauthor;
ALTER TABLE GitRef ADD COLUMN author_date timestamp without time zone;
ALTER TABLE GitRef ADD COLUMN committer integer REFERENCES revisionauthor;
ALTER TABLE GitRef ADD COLUMN committer_date timestamp without time zone;
ALTER TABLE GitRef ADD COLUMN commit_message text;

COMMENT ON COLUMN GitRef.object_type IS 'The type of object pointed to by this reference.';
COMMENT ON COLUMN GitRef.author IS 'The author of the commit pointed to by this reference.';
COMMENT ON COLUMN GitRef.author_date IS 'The author date of the commit pointed to by this reference.';
COMMENT ON COLUMN GitRef.committer IS 'The committer of the commit pointed to by this reference.';
COMMENT ON COLUMN GitRef.committer_date IS 'The committer date of the commit pointed to by this reference.';
COMMENT ON COLUMN GitRef.commit_message IS 'The commit message of the commit pointed to by this reference.';

CREATE TABLE GitJob (
    job integer PRIMARY KEY REFERENCES job ON DELETE CASCADE UNIQUE NOT NULL,
    repository integer NOT NULL REFERENCES gitrepository,
    job_type integer NOT NULL,
    json_data text
);

COMMENT ON TABLE GitJob IS 'Contains references to jobs that are executed for a Git repository.';
COMMENT ON COLUMN GitJob.job IS 'A reference to a Job row that has all the common job details.';
COMMENT ON COLUMN GitJob.repository IS 'The repository that this job is for.';
COMMENT ON COLUMN GitJob.job_type IS 'The type of job, such as a ref scan.';
COMMENT ON COLUMN GitJob.json_data IS 'Data that is specific to a particular job type.';

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 61, 2);
