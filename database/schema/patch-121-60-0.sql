SET client_min_messages=ERROR;

-- Allow two or more identical devices in a submission.

ALTER TABLE HWSubmissionDevice DROP CONSTRAINT
    hwsubmissiondevice__devicer_driver_link__submission__key;
CREATE INDEX hwsubmissiondevice__device_driver_link__idx
    ON HWSubmissionDevice(device_driver_link);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 60, 0);
