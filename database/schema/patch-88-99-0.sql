CREATE TABLE HWDriver (
    id serial PRIMARY KEY,
    package_name text,
    name text NOT NULL,
    license integer REFERENCES License(id),
    CONSTRAINT hwdriver__package_name__name__key UNIQUE(package_name, name)
    );
CREATE INDEX hwdriver__package_name__idx ON HWDriver USING btree(package_name);
CREATE INDEX hwdriver__name__idx ON HWDriver USING btree(name);

-- The names of busses like SCSI, PCI, USB.
CREATE TABLE HWBus (
    id serial PRIMARY KEY,
    name text UNIQUE NOT NULL
    );

-- A list of vendor names.
CREATE TABLE HWVendorName (
    id serial PRIMARY KEY,
    name text UNIQUE NOT NULL
    );
CREATE INDEX hwvendorname__name__idx ON HWDriver USING btree(name);

-- Association of (bus, vendor ID for this bus) with a vendor name.
CREATE TABLE HWVendorId (
    id serial PRIMARY KEY,
    bus integer REFERENCES HWBus(id) NOT NULL,
    vendor_id_for_bus text NOT NULL,
    vendor_name integer REFERENCES HWVendorName(id) NOT NULL,
    CONSTRAINT hwvendorid__bus_vendor_id__vendor_name__key
        UNIQUE (bus, vendor_id_for_bus, vendor_name)
    );
CREATE INDEX hwvendorid__bus__idx ON HWVendorId USING btree(bus);
CREATE INDEX hwvendorid__vendor_id_for_bus__idx ON HWVendorId 
    USING btree(vendor_id_for_bus);
CREATE INDEX hwvendorid__vendorname__idx ON HWVendorId USING btree(vendor_name);
-- Core device data.
CREATE TABLE HWDevice (
    id serial PRIMARY KEY,
    bus_vendor_id integer REFERENCES HWVendorId(id) NOT NULL,
    bus_product_id text NOT NULL,
    variant text,
    name text NOT NULL,
    submissions integer NOT NULL,
    CONSTRAINT hwdevice__bus_vendor_id__bus_product_id__variant__key
        UNIQUE(bus_vendor_id, bus_product_id, variant)
    );
CREATE INDEX hwdevice__bus_vendor_id__idx ON HWDevice
    USING btree(bus_vendor_id);
CREATE INDEX hwdevice__bus_product_id__idx ON HWDevice
    USING btree(bus_product_id);
CREATE INDEX hwdevice__name__idx ON HWDevice
    USING btree(name);

-- Alternative names of a device.
CREATE TABLE HWDeviceNameVariant (
    id serial PRIMARY KEY,
    vendor_name integer REFERENCES HWVendorName(id) NOT NULL,
    product_name text NOT NULL,
    device integer REFERENCES HWDevice(id) NOT NULL,
    submissions integer NOT NULL,
    CONSTRAINT hwdevicenamevariant__vendor__product_name__device__key 
        UNIQUE (vendor_name, product_name, device)
    );
CREATE INDEX hwdevicenamevariant__vendor_name__idx ON HWDeviceNameVariant
    USING btree(vendor_name);
CREATE INDEX hwdevicenamevariant__product_name__idx ON HWDeviceNameVariant
    USING btree(product_name);
CREATE INDEX hwdevicenamevariant__device__idx ON HWDeviceNameVariant
    USING btree(device);

-- Associate a device with a driver.
CREATE TABLE HWDeviceDriverLink (
    id serial PRIMARY KEY,
    device integer REFERENCES HWDevice(id) NOT NULL,
    driver integer REFERENCES HWDriver(id),
    CONSTRAINT hwdevicedriverlink__device__driver__key UNIQUE (device, driver)
    );
CREATE INDEX hwdevicedriverlink__device__idx ON HWDeviceDriverLink
    USING btree(device);
CREATE INDEX hwdevicedriverlink__driver__idx ON HWDeviceDriverLink
    USING btree(driver);

-- Link a device from a submission to a device/driver tuple.
CREATE TABLE HWSubmissionDevice (
    id serial PRIMARY KEY,
    device_driver_link integer REFERENCES HWDeviceDriverLink(id) NOT NULL,
    submission integer REFERENCES HWSubmission(id) NOT NULL,
    parent integer REFERENCES HWSubmissionDevice(id),
    CONSTRAINT hwsubmissiondevice__devicer_driver_link__submission__key
        UNIQUE (device_driver_link, submission)
    );
CREATE INDEX hwsubmissiondevice__device_driver_link__idx ON HWSubmissionDevice
    USING btree(device_driver_link);
CREATE INDEX hwsubmissiondevice__submission__idx ON HWSubmissionDevice
    USING btree(submission);

-- Test data.
CREATE TABLE HWTest (
    id serial PRIMARY KEY,
    namespace text,
    name text NOT NULL,
    version text NOT NULL,
    CONSTRAINT hwtest__namespace__name__version__key 
        UNIQUE (namespace, name, version)
    );
CREATE INDEX hwtest__namespace__idx ON HWTest USING btree(namespace);
CREATE INDEX hwtest__name__idx ON HWTest USING btree(name);

-- For tests with multiple choice questions: Available choice values.
CREATE TABLE HWTestAnswerChoice (
    id serial PRIMARY KEY,
    choice text NOT NULL,
    test integer REFERENCES HWTest(id) NOT NULL,
    CONSTRAINT hwtestanswerchoice__choice__test__key UNIQUE (choice, test)
    );
CREATE INDEX hwtestanswerchoice__choice__idx ON HWTestAnswerChoice
    USING btree(choice);
CREATE INDEX hwtestanswerchoice__test__idx ON HWTestAnswerChoice
    USING btree(test);

CREATE TABLE HWTestAnswer (
    id serial PRIMARY KEY,
    test integer REFERENCES HWTest(id) NOT NULL,
    choice integer REFERENCES HWTestAnswerChoice(id),
    intval integer,
    floatval double precision,
    unit text,
    comment text,
    language integer REFERENCES Language(id),
    submission integer REFERENCES HWSubmission(id) NOT NULL,
    CHECK ((choice = null AND unit != NULL AND
            ((intval != NULL AND floatval = NULL) OR
             (intval = NULL AND floatval != NULL))
           )
        OR (choice != null AND unit = NULL AND intval = NULL AND 
            floatval = NULL))
    );
CREATE INDEX hwtestanswer__test__idx ON HWTestAnswer USING btree(test);
CREATE INDEX hwtestanswer__choice__idx ON HWTestAnswer USING btree(choice);

CREATE TABLE HWTestAnswerCount (
    id serial PRIMARY KEY,
    test integer REFERENCES HWTest(id),
    distroarchrelease integer REFERENCES DistroArchRelease(id),
    choice integer REFERENCES HWTestAnswerChoice(id),
    average double precision,
    sum_square double precision,
    unit text,
    num_answers integer NOT NULL,
    CHECK ((choice = null AND average != null AND sum_square != null AND
           unit != NULL)
        OR (choice != null AND average = null AND sum_square = null AND
           unit = NULL))
    );
CREATE INDEX hwtestanswercount__test__idx ON HWTestAnswerCount
    USING btree(test);
CREATE INDEX hwtestanswercount__distroarchrelease__idx ON HWTestAnswerCount
    USING btree(distroarchrelease);
CREATE INDEX hwtestanswercount__choice__idx ON HWTestAnswerCount
    USING btree(choice);

-- link a device and a driver with a test answer.
CREATE TABLE HWTestAnswerDevice (
    id serial PRIMARY KEY,
    answer integer REFERENCES HWTestAnswer(id) NOT NULL,
    device_driver integer REFERENCES HWDeviceDriverLink(id),
    CONSTRAINT hwtestanswerdevice__answer__device_driver_key 
        UNIQUE (answer, device_driver)
    );
CREATE INDEX hwtestanswerdevice__answer__idx ON HWTestAnswerDevice
    USING btree(answer);
CREATE INDEX hwtestanswerdevice__device_driver__idx ON HWTestAnswerDevice
    USING btree(device_driver);

-- link a device and a driver with a test answer count row.
CREATE TABLE HWTestAnswerCountDevice (
    id serial PRIMARY KEY,
    answer integer REFERENCES HWTestAnswerCount(id),
    device_driver integer REFERENCES HWDeviceDriverLink(id),
    CONSTRAINT hwtestanswercountdevice__answer__device_driver_key 
        UNIQUE (answer, device_driver)
    );
CREATE INDEX hwtestanswercountdevice__answer__idx ON HWTestAnswerCountDevice
    USING btree(answer);
CREATE INDEX hwtestanswercountdevice__device_driver__idx ON 
    HWTestAnswerCountDevice USING btree(device_driver);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
