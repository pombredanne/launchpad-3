SET client_min_messages=ERROR;

CREATE TABLE HWDeviceClass (
    id SERIAL PRIMARY KEY,
    device INTEGER NOT NULL REFERENCES HWDevice(id),
    main_class INTEGER NOT NULL,
    sub_class INTEGER,
    CONSTRAINT hwdeviceclass__device__main_class__sub_class__idx
        UNIQUE (device, main_class, sub_class)
);

CREATE INDEX hwdeviceclass__main_class__idx ON HWDeviceClass(main_class);
CREATE INDEX hwdeviceclass__sub_class__idx ON HWDeviceClass(sub_class);
CREATE UNIQUE INDEX hwdeviceclass__device__main_class_unique__idx
    ON HWDeviceClass(device, main_class) WHERE sub_class IS NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
