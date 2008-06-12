SET client_min_messages=ERROR;

-- Allow two or more identical devices in a submission.

ALTER TABLE HWSubmissionDevice DROP CONSTRAINT hwsubmissiondevice__devicer_driver_link__submission__key;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
