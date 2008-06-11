SET client_min_messages=ERROR;

-- Relate a HWSubmissionDevice record with its respective HAL node
-- from the submitted data.

ALTER TABLE HWSubmissionDevice ADD COLUMN hal_device_id int NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
