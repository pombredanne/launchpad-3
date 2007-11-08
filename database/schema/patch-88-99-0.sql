CREATE TABLE HWDriver (
    id serial PRIMARY KEY,
    package text,
    name text NOT NULL,
    license integer REFERENCES License(id),
    CONSTRAINT hwdriver__package__name__key UNIQUE(package, name)
    );

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

-- Association of (bus, vendor ID for this bus) with a vendor name.
CREATE TABLE HWVendorId (
    id serial PRIMARY KEY,
    bus integer REFERENCES HWBus(id) NOT NULL,
    vendor_id_for_bus text NOT NULL,
    vendor_name integer REFERENCES HWVendorName(id) NOT NULL,
    CONSTRAINT hwvendorid__bus_vendor_id__vendor_name__key
        UNIQUE (bus, vendor_id_for_bus, vendor_name)
    );

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

-- Associate a device with a driver.
CREATE TABLE HWDeviceDriverLink (
    id serial PRIMARY KEY,
    device integer REFERENCES HWDevice(id) NOT NULL,
    driver integer REFERENCES HWDriver(id),
    CONSTRAINT hwdevicedriverlink__device__driver__key UNIQUE (device, driver)
    );

-- Link a device from a submission to a device/driver tuple.
CREATE TABLE HWSubmissionDevice (
    id serial PRIMARY KEY,
    device_driver_link integer REFERENCES HWDeviceDriverLink(id) NOT NULL,
    submission integer REFERENCES HWSubmission(id) NOT NULL,
    parent integer REFERENCES HWSubmissionDevice(id),
    CONSTRAINT hwsubmissiondevice__devicer_driver_link__submission__key
        UNIQUE (device_driver_link, submission)
    );

-- Test data.
CREATE TABLE HWTest (
    id serial PRIMARY KEY,
    namespace text,
    name text NOT NULL,
    version text NOT NULL,
    CONSTRAINT hwtest__namespace__name__version__key 
        UNIQUE (namespace, name, version)
    );

-- For tests with multiple choice questions: Available choice values.
CREATE TABLE HWTestAnswerChoice (
    id serial PRIMARY KEY,
    choice text NOT NULL,
    test integer REFERENCES HWTest(id) NOT NULL,
    CONSTRAINT hwtestanswerchoice__choice__test__key UNIQUE (choice, test)
    );

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

-- link a device and a driver with a test answer.
CREATE TABLE HWTestAnswerDevice (
    id serial PRIMARY KEY,
    answer integer REFERENCES HWTestAnswer(id) NOT NULL,
    device_driver integer REFERENCES HWDeviceDriverLink(id),
    CONSTRAINT hwtestanswerdevice__answer__device_driver_key 
        UNIQUE (answer, device_driver)
    );

-- link a device and a driver with a test answer count row.
CREATE TABLE HWTestAnswerCountDevice (
    id serial PRIMARY KEY,
    answer integer REFERENCES HWTestAnswerCount(id),
    device_driver integer REFERENCES HWDeviceDriverLink(id),
    CONSTRAINT hwtestanswercountdevice__answer__device_driver_key 
        UNIQUE (answer, device_driver)
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 99, 0);
