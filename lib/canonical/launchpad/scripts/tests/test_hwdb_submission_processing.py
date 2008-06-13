# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Tests of the HWDB submissions parser."""

import logging
from unittest import TestCase, TestLoader

from zope.testing.loghandler import Handler

from canonical.launchpad.interfaces.hwdb import HWBus
from canonical.launchpad.scripts.hwdbsubmissions import (
    HALDevice, PCI_CLASS_BRIDGE, PCI_CLASS_SERIALBUS_CONTROLLER,
    PCI_CLASS_STORAGE, PCI_SUBCLASS_BRIDGE_CARDBUS, PCI_SUBCLASS_BRIDGE_PCI,
    PCI_SUBCLASS_SERIALBUS_USB, PCI_SUBCLASS_STORAGE_SATA, SubmissionParser)
from canonical.testing import BaseLayer


class TestCaseHWDB(TestCase):
    """Common base class for HWDB processing tests."""

    layer = BaseLayer

    UDI_COMPUTER = '/org/freedesktop/Hal/devices/computer'
    UDI_SATA_CONTROLLER = '/org/freedesktop/Hal/devices/pci_8086_27c5'
    UDI_SATA_CONTROLLER_SCSI = ('/org/freedesktop/Hal/devices/'
                               'pci_8086_27c5_scsi_host')
    UDI_SATA_DISK = ('org/freedesktop/Hal/devices/'
                     'pci_8086_27c5_scsi_host_scsi_device_lun0')
    UDI_USB_CONTROLLER_PCI_SIDE = '/org/freedesktop/Hal/devices/pci_8086_27cc'
    UDI_USB_CONTROLLER_USB_SIDE = ('/org/freedesktop/Hal/devices/'
                                   'usb_device_0_0_0000_00_1d_7')
    UDI_USB_CONTROLLER_USB_SIDE_RAW = ('/org/freedesktop/Hal/devices/'
                                   'usb_device_0_0_0000_00_1d_7_usbraw')
    UDI_USB_STORAGE = '/org/freedesktop/Hal/devices/usb_device_1307_163_07'
    UDI_USB_STORAGE_IF0 = ('/org/freedesktop/Hal/devices/'
                           'usb_device_1307_163_07_if0')
    UDI_USB_STORAGE_SCSI_HOST = ('/org/freedesktop/Hal/devices/'
                                 'usb_device_1307_163_07_if0scsi_host')
    UDI_USB_STORAGE_SCSI_DEVICE = ('/org/freedesktop/Hal/devices/'
                                   'usb_device_1307_163_07_if0'
                                   'scsi_host_scsi_device_lun0')
    UDI_USB_HUB = '/org/freedesktop/Hal/devices/usb_device_409_5a_noserial'
    UDI_USB_HUB_IF0 = ('/org/freedesktop/Hal/devices/'
                       'usb_dev_409_5a_noserial_if0')
    UDI_PCI_PCI_BRIDGE = '/org/freedesktop/Hal/devices/pci_8086_2448'
    UDI_PCI_PCCARD_BRIDGE = '/org/freedesktop/Hal/devices/pci_1217_7134'
    UDI_PCCARD_DEVICE = '/org/freedesktop/Hal/devices/pci_9004_6075'

    UDI_SCSI_DISK = '/org/freedesktop/Hal/devices/scsi_disk'

    PCI_VENDOR_ID_INTEL = 0x8086

    USB_VENDOR_ID_NEC = 0x0409
    USB_PROD_ID_NEC_HUB = 0x005a

    USB_VENDOR_ID_USBEST = 0x1307
    USB_PROD_ID_USBBEST_MEMSTICK = 0x0163

    def setUp(self):
        """Setup the test environment."""
        self.log = logging.getLogger('test_hwdb_submission_parser')
        self.log.setLevel(logging.INFO)
        self.handler = Handler(self)
        self.handler.add(self.log.name)

    def assertWarningMessage(self, submission_key, log_message):
        """Search for message in the log entries for submission_key.

        :raise: AssertionError if no log message exists that starts with
            "Parsing submission <submission_key>:" and that contains
            the text passed as the parameter message.
        """
        expected_message = 'Parsing submission %s: %s' % (
            submission_key, log_message)

        for record in self.handler.records:
            if record.levelno != logging.WARNING:
                continue
            candidate = record.getMessage()
            if candidate == expected_message:
                return
        raise AssertionError('No log message found: %s' % expected_message)


class TestHWDBSubmissionProcessing(TestCaseHWDB):
    """Tests for processing of HWDB submissions."""

    def testBuildDeviceList(self):
        """Test the creation of list HALDevice instances for a submission."""
        devices = [
            {
                'id': 1,
                'udi': self.UDI_COMPUTER,
                'properties': {},
                },
            {
                'id': 2,
                'udi': self.UDI_SATA_CONTROLLER,
                'properties': {
                    'info.parent': (self.UDI_COMPUTER, 'str')
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        self.assertEqual(len(parser.hal_devices), len(devices),
                         'Numbers of devices in parser.hal_devices and in '
                         'sample data are different')
        root_device = parser.hal_devices[self.UDI_COMPUTER]
        self.assertEqual(root_device.id, 1,
                         'Unexpected value of root device ID.')
        self.assertEqual(root_device.udi, self.UDI_COMPUTER,
                         'Unexpected value of root device UDI.')
        self.assertEqual(root_device.properties,
                         devices[0]['properties'],
                         'Unexpected properties of root device.')
        child_device = parser.hal_devices[self.UDI_SATA_CONTROLLER]
        self.assertEqual(child_device.id, 2,
                         'Unexpected value of child device ID.')
        self.assertEqual(child_device.udi, self.UDI_SATA_CONTROLLER,
                         'Unexpected value of child device UDI.')
        self.assertEqual(child_device.properties,
                         devices[1]['properties'],
                         'Unexpected properties of child device.')

        parent = parser.hal_devices[self.UDI_COMPUTER]
        child = parser.hal_devices[self.UDI_SATA_CONTROLLER]
        self.assertEqual(parent.children, [child],
                         'Child missing in parent.children.')
        self.assertEqual(child.parent, parent,
                         'Invalid value of child.parent.')

    def testHALDeviceConstructor(self):
        """Test of the HALDevice constructor."""
        properties = {
            'info.bus': ('scsi', 'str'),
            }
        parser = SubmissionParser(self.log)
        device = HALDevice(1, '/some/udi/path', properties, parser)

        self.assertEqual(device.id, 1, 'Unexpected device ID')
        self.assertEqual(device.udi, '/some/udi/path',
                         'Unexpected device UDI.')
        self.assertEqual(device.properties, properties,
                         'Unexpected device properties.')
        self.assertEqual(device.parser, parser,
                         'Unexpected device parser.')

    def testHALDeviceGetProperty(self):
        """Test of HALDevice.getProperty."""
        properties = {
            'info.bus': ('scsi', 'str'),
            }
        parser = SubmissionParser(self.log)
        device = HALDevice(1, '/some/udi/path', properties, parser)

        # HALDevice.getProperty returns the value of a HAL property.
        # Note that the property type is _not_ returned
        self.assertEqual(device.getProperty('info.bus'), 'scsi',
            'Unexpected result of calling HALDevice.getProperty.')
        # If a property of the given name does not exist, None is returned.
        self.assertEqual(device.getProperty('does-not-exist'), None,
            'Unexpected result of calling HALDevice.getProperty for a '
            'non-existing property.')

    def testHALDeviceParentUDI(self):
        """Test of HALDevice.parent_udi."""
        properties = {
            'info.bus': ('scsi', 'str'),
            'info.parent': ('/another/udi', 'str'),
            }
        parser = SubmissionParser(self.log)
        device = HALDevice(1, '/some/udi/path', properties, parser)
        self.assertEqual(device.parent_udi, '/another/udi',
                         'Unexpected value of HALDevice.parent_udi.')

        properties = {
            'info.bus': ('scsi', 'str'),
            }
        parser = SubmissionParser(self.log)
        device = HALDevice(1, '/some/udi/path', properties, parser)
        self.assertEqual(device.parent_udi, None,
                         'Unexpected value of HALDevice.parent_udi, '
                         'when no parent information available.')

    def testHALDeviceGetBus(self):
        """Test of HALDevice.getBus, generic case.

        For most buses as "seen" by HAL, HALDevice.getBus returns a
        unique HWBus value.
        """
        for hal_bus, real_bus in (('usb_device', HWBus.USB),
                                  ('pcmcia', HWBus.PCMCIA),
                                  ('ide', HWBus.IDE),
                                  ('serio', HWBus.SERIAL),
                                 ):
            UDI_TEST_DEVICE = '/org/freedesktop/Hal/devices/test_device'
            devices = [
                {
                    'id': 1,
                    'udi': UDI_TEST_DEVICE,
                    'properties': {
                        'info.bus': (hal_bus, 'str'),
                        },
                    },
                ]
            parsed_data = {
                'hardware': {
                    'hal': {'devices': devices,
                        },
                    },
                }
            parser = SubmissionParser(self.log)
            parser.buildDeviceList(parsed_data)
            test_device = parser.hal_devices[UDI_TEST_DEVICE]
            test_bus = test_device.getBus()
            self.assertEqual(test_bus, real_bus,
                             'Unexpected result of HALDevice.getBus for '
                             'HAL bus %s: %s.' % (hal_bus, test_bus.title))

    def testHALDeviceGetBusSystem(self):
        """Test of HALDevice.getBus, for the tested machine itself."""

        devices = [
            {
                'id': 1,
                'udi': self.UDI_COMPUTER,
                'properties': {
                    'info.bus': ('unknown', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        test_device = parser.hal_devices[self.UDI_COMPUTER]
        test_bus = test_device.getBus()
        self.assertEqual(test_bus, HWBus.SYSTEM,
                         'Unexpected result of HALDevice.getBus for '
                         'a system: %s' % test_bus.title)

    def testHALDeviceGetBusScsiUsb(self):
        """Test of HALDevice.getBus for info.bus=='scsi' and a USB device.

        Memory sticks, card readers and USB->IDE/SATA adapters use SCSI
        emulation; HALDevice.getBus treats these devices as "black boxes",
        and thus returns None.
        """
        devices = [
            # The main node of the USB storage device.
            {
                'id': 1,
                'udi': self.UDI_USB_STORAGE,
                'properties': {
                    'info.bus': ('usb_device', 'str'),
                    },
                },
            # The storage interface of the USB device.
            {
                'id': 2,
                'udi': self.UDI_USB_STORAGE_IF0,
                'properties': {
                    'info.bus': ('usb', 'str'),
                    'info.parent': (self.UDI_USB_STORAGE, 'str'),
                    },
                },
            # The fake SCSI host of the storage device. Note that HAL does
            # _not_ provide the info.bus property.
            {
                'id': 3,
                'udi': self.UDI_USB_STORAGE_SCSI_HOST,
                'properties': {
                    'info.parent': (self.UDI_USB_STORAGE_IF0, 'str'),
                    },
                },
            # The fake SCSI disk.
            {
                'id': 3,
                'udi': self.UDI_USB_STORAGE_SCSI_DEVICE,
                'properties': {
                    'info.bus': ('scsi', 'str'),
                    'info.parent': (self.UDI_USB_STORAGE_SCSI_HOST, 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {'devices': devices,
                    },
                },
            }

        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)

        usb_fake_scsi_disk = parser.hal_devices[
            self.UDI_USB_STORAGE_SCSI_DEVICE]
        self.assertEqual(usb_fake_scsi_disk.getBus(), None,
            'Unexpected result of HALDevice.getBus for the fake SCSI disk '
            'HAL node of a USB storage device bus.')

    def testHALDeviceGetBusScsiPci(self):
        """Test of HALDevice.getBus for info.bus=='scsi' and a PCI controller.

        The real bus for this device can be IDE, ATA, SATA or SCSI.
        """
        devices = [
            # The PCI host controller.
            {
                'id': 1,
                'udi': self.UDI_SATA_CONTROLLER,
                'properties': {
                    'info.bus': ('pci', 'str'),
                    'pci.device_class': (PCI_CLASS_STORAGE, 'int'),
                    'pci.device_subclass': (PCI_SUBCLASS_STORAGE_SATA,
                                            'int'),
                    },
                },
            # The fake SCSI host of the storage device. Note that HAL does
            # _not_ provide the info.bus property.
            {
                'id': 2,
                'udi': self.UDI_SATA_CONTROLLER_SCSI,
                'properties': {
                    'info.parent': (self.UDI_SATA_CONTROLLER, 'str'),
                    },
                },
            # The (possibly fake) SCSI disk.
            {
                'id': 3,
                'udi': self.UDI_SATA_DISK,
                'properties': {
                    'info.bus': ('scsi', 'str'),
                    'info.parent': (self.UDI_SATA_CONTROLLER_SCSI, 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {'devices': devices,
                    },
                },
            }

        pci_subclass_bus = (
            (0, HWBus.SCSI),
            (1, HWBus.IDE),
            (2, HWBus.FLOPPY),
            (3, HWBus.IPI),
            (4, None), # subclass RAID is ignored.
            (5, HWBus.ATA),
            (6, HWBus.SATA),
            (7, HWBus.SAS),
            )

        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)

        for device_subclass, expected_bus in pci_subclass_bus:
            devices[0]['properties']['pci.device_subclass'] = (
                device_subclass, 'int')
            fake_scsi_disk = parser.hal_devices[self.UDI_SATA_DISK]
            found_bus = fake_scsi_disk.getBus()
            self.assertEqual(found_bus, expected_bus,
                'Unexpected result of HWDevice.getBus for PCI storage '
                'class device, subclass %i: %r.' % (device_subclass,
                                                    found_bus))

    def testHALDeviceGetBusPci(self):
        """Test of HALDevice.getBus for info.bus=='pci'.

        If info.bus == 'pci', we may have a real PCI device or a PCCard.
        """
        # possible parent device for the tested device,
        parent_devices = [
            # The host itself.
            {
                'id': 1,
                'udi': self.UDI_COMPUTER,
                'properties': {
                    'info.bus': ('unknown', 'str'),
                    },
                },
            # A PCI->PCI bridge.
            {
                'id': 2,
                'udi': self.UDI_PCI_PCI_BRIDGE,
                'properties': {
                    'info.parent': (self.UDI_COMPUTER, 'str'),
                    'info.bus': ('pci', 'str'),
                    'pci.device_class': (PCI_CLASS_BRIDGE, 'int'),
                    'pci.device_subclass': (PCI_SUBCLASS_BRIDGE_PCI, 'int'),
                    },
                },
            # A PCI->PCCard bridge.
            {
                'id': 3,
                'udi': self.UDI_PCI_PCCARD_BRIDGE,
                'properties': {
                    'info.parent': (self.UDI_PCI_PCI_BRIDGE, 'str'),
                    'info.bus': ('pci', 'str'),
                    'pci.device_class': (PCI_CLASS_BRIDGE, 'int'),
                    'pci.device_subclass': (PCI_SUBCLASS_BRIDGE_CARDBUS,
                                            'int'),
                    },
                },
        ]
        tested_device = {
            'id': 4,
            'udi': self.UDI_PCCARD_DEVICE,
            'properties': {
                'info.bus': ('pci', 'str'),
                },
            }
        parsed_data = {
            'hardware': {
                'hal': {},
                },
            }
        expected_result_for_parent_device = {
            self.UDI_COMPUTER: HWBus.PCI,
            self.UDI_PCI_PCI_BRIDGE: HWBus.PCI,
            self.UDI_PCI_PCCARD_BRIDGE: HWBus.PCCARD,
            }

        parser = SubmissionParser(self.log)

        for parent_device in parent_devices:
            devices = parent_devices[:]
            tested_device['properties']['info.parent'] = (
                parent_device['udi'], 'str')
            devices.append(tested_device)
            parsed_data['hardware']['hal']['devices'] = devices
            parser.buildDeviceList(parsed_data)
            tested_hal_device = parser.hal_devices[self.UDI_PCCARD_DEVICE]
            found_bus = tested_hal_device.getBus()
            expected_bus = expected_result_for_parent_device[
                parent_device['udi']]
            self.assertEqual(found_bus, expected_bus,
                             'Unexpected result of HWDevice.getBus for a '
                             'PCI or PCCard device: Expected %r, got %r.'
                             % (expected_bus, found_bus))

    def testHALDeviceGetBusUnknown(self):
        """Test of HALDevice.getBus for unknown values of info.bus."""
        devices = [
            {
                'id': 1,
                'udi': self.UDI_PCCARD_DEVICE,
                'properties': {
                    'info.bus': ('nonsense', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {'devices': devices,
                    },
                },
            }

        parser = SubmissionParser(self.log)
        parser.submission_key = 'Test of unknown bus name'
        parser.buildDeviceList(parsed_data)
        found_bus = parser.hal_devices[self.UDI_PCCARD_DEVICE].getBus()
        self.assertEqual(found_bus, None,
                         'Unexpected result of HWDevice.getBus for an '
                         'unknown bus name: Expected None, got %r.'
                         % found_bus)
        self.assertWarningMessage(
            parser.submission_key,
            "Unknown bus 'nonsense' for device " + self.UDI_PCCARD_DEVICE)

    def testHALDeviceRealDeviceRegularBus(self):
        """Test of HALDevice.is_real_device: regular info.bus property.

        See below for exceptions, if info.bus == 'usb_device' or if
        info.bus == 'usb'.
        """
        # If a HAL device has the property info.bus, it is considered
        # to be a real device.
        devices = [
            {
                'id': 1,
                'udi': self.UDI_USB_CONTROLLER_PCI_SIDE,
                'properties': {
                    'info.bus': ('pci', 'str'),
                    'pci.device_class': (PCI_CLASS_SERIALBUS_CONTROLLER,
                                         'int'),
                    'pci.device_subclass': (PCI_SUBCLASS_SERIALBUS_USB,
                                            'int'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        device = parser.hal_devices[self.UDI_USB_CONTROLLER_PCI_SIDE]
        self.failUnless(device.is_real_device,
                        'Device with info.bus property not treated as a '
                        'real device')

    def testHALDeviceRealDeviceNoBus(self):
        """Test of HALDevice.is_real_device: No info.bus property."""
        UDI_HAL_STORAGE_DEVICE = '/org/freedesktop/Hal/devices/storage...'
        devices = [
            {
                'id': 1,
                'udi': UDI_HAL_STORAGE_DEVICE,
                'properties': {},
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {'devices': devices,
                    },
                },
            }

        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        device = parser.hal_devices[UDI_HAL_STORAGE_DEVICE]
        self.failIf(device.is_real_device,
                    'Device without info.bus property treated as a '
                    'real device')

    def testHALDeviceRealDeviceHALBusValueIgnored(self):
        """Test of HALDevice.is_real_device: ignored values of info.bus.

        A HAL device is considered to not be a real device, if its
        info.bus proerty is 'platform', 'pnp' or 'usb'.
        """
        devices = [
            {
                'id': 1,
                'udi': self.UDI_USB_HUB_IF0,
                'properties': {},
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {'devices': devices,
                    },
                },
            }

        properties = devices[0]['properties']
        parser = SubmissionParser(self.log)

        for bus in ('platform', 'pnp', 'usb'):
            properties['info.bus'] = (bus, 'str')
            parser.buildDeviceList(parsed_data)
            device = parser.hal_devices[self.UDI_USB_HUB_IF0]
            self.failIf(device.is_real_device,
                        'Device with info.bus=%r treated as a real device'
                        % bus)

    def testHALDeviceRealDeviceScsiDevicesPciController(self):
        """Test of HALDevice.is_real_device: info.bus == 'scsi'.

        The (fake or real) SCSI device is connected to a PCI controller.
        Though the real bus may not be SCSI, all devices for the busses
        SCSI, IDE, ATA, SATA, SAS are treated as real devices.
        """
        devices = [
            # The PCI host controller.
            {
                'id': 1,
                'udi': self.UDI_SATA_CONTROLLER,
                'properties': {
                    'info.bus': ('pci', 'str'),
                    'pci.device_class': (PCI_CLASS_STORAGE, 'int'),
                    'pci.device_subclass': (PCI_SUBCLASS_STORAGE_SATA, 'int'),
                    },
                },
            # The (possibly fake) SCSI host of the storage device.
            {
                'id': 3,
                'udi': self.UDI_SATA_CONTROLLER_SCSI,
                'properties': {
                    'info.parent': (self.UDI_SATA_CONTROLLER,
                                    'str'),
                    },
                },
            # The (possibly fake) SCSI disk.
            {
                'id': 3,
                'udi': self.UDI_SATA_DISK,
                'properties': {
                    'info.bus': ('scsi', 'str'),
                    'info.parent': (self.UDI_SATA_CONTROLLER_SCSI, 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {'devices': devices,
                    },
                },
            }

        pci_subclass_bus = (
            (0, True), # a real SCSI controller
            (1, True), # an IDE device
            (4, False), # subclass RAID is ignored.
            (5, True), # an ATA device
            (6, True), # a SATA device
            (7, True), # a SAS device
            )

        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)

        for device_subclass, expected_is_real in pci_subclass_bus:
            devices[0]['properties']['pci.device_subclass'] = (
                device_subclass, 'int')
            scsi_device = parser.hal_devices[self.UDI_SATA_DISK]
            found_is_real = scsi_device.is_real_device
            self.assertEqual(found_is_real, expected_is_real,
                'Unexpected result of HWDevice.is_real_device for a HAL SCSI '
                'connected to PCI controller, subclass %i: %r'
                % (device_subclass, found_is_real))

    def testHALDeviceRealDeviceScsiDeviceUsbStorage(self):
        """Test of HALDevice.is_real_device: info.bus == 'scsi'.

        USB storage devices are treated as SCSI devices by HAL;
        we do not consider them to be real devices.
        """
        devices = [
            # The main node of the USB storage device.
            {
                'id': 1,
                'udi': self.UDI_USB_STORAGE,
                'properties': {
                    'info.bus': ('usb_device', 'str'),
                    },
                },
            # The storage interface of the USB device.
            {
                'id': 2,
                'udi': self.UDI_USB_STORAGE_IF0,
                'properties': {
                    'info.bus': ('usb', 'str'),
                    'info.parent': (self.UDI_USB_STORAGE, 'str'),
                    },
                },
            # The fake SCSI host of the storage device. Note that HAL does
            # _not_ provide the info.bus property.
            {
                'id': 3,
                'udi': self.UDI_USB_STORAGE_SCSI_HOST,
                'properties': {
                    'info.parent': (self.UDI_USB_STORAGE_IF0, 'str'),
                    },
                },
            # The fake SCSI disk.
            {
                'id': 3,
                'udi': self.UDI_USB_STORAGE_SCSI_DEVICE,
                'properties': {
                    'info.bus': ('scsi', 'str'),
                    'info.parent': (self.UDI_USB_STORAGE_SCSI_HOST, 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {'devices': devices,
                    },
                },
            }

        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)

        scsi_device = parser.hal_devices[self.UDI_USB_STORAGE_SCSI_DEVICE]
        self.failIf(scsi_device.is_real_device,
            'Unexpected result of HWDevice.is_real_device for a HAL SCSI '
            'device as a subdevice of a USB storage device.')

    def testHALDeviceRealChildren(self):
        """Test of HALDevice.getRealChildren."""
        # An excerpt of a real world HAL device tree. We have three "real"
        # devices, and two "unreal" devices (ID 3 and 4)
        #
        # the host itself. Treated as a real device.
        devices = [
            {
                'id': 1,
                'udi': self.UDI_COMPUTER,
                'properties': {}
                },
            # A PCI->USB bridge.
            {
                'id': 2,
                'udi': self.UDI_USB_CONTROLLER_PCI_SIDE,
                'properties': {
                    'info.parent': (self.UDI_COMPUTER, 'str'),
                    'info.bus': ('pci', 'str'),
                    'pci.device_class': (PCI_CLASS_SERIALBUS_CONTROLLER,
                                         'int'),
                    'pci.device_subclass': (PCI_SUBCLASS_SERIALBUS_USB,
                                            'int'),
                 }
            },
            # The "output aspect" of the PCI->USB bridge. Not a real
            # device.
            {
                'id': 3,
                'udi': self.UDI_USB_CONTROLLER_USB_SIDE,
                'properties': {
                    'info.parent': (self.UDI_USB_CONTROLLER_PCI_SIDE, 'str'),
                    'info.bus': ('usb_device', 'str'),
                    'usb_device.vendor_id': (0, 'int'),
                    'usb_device.product_id': (0, 'int'),
                    },
                },
            # The HAL node for raw USB data access of the bridge. Not a
            # real device.
            {
                'id': 4,
                'udi': self.UDI_USB_CONTROLLER_USB_SIDE_RAW,
                'properties': {
                    'info.parent': (self.UDI_USB_CONTROLLER_USB_SIDE, 'str'),
                    },
                },
            # The HAL node of a USB device connected to the bridge.
            {
                'id': 5,
                'udi': self.UDI_USB_HUB,
                'properties': {
                    'info.parent': (self.UDI_USB_CONTROLLER_USB_SIDE, 'str'),
                    'info.bus': ('usb_device', 'str'),
                    'usb_device.vendor_id': (self.USB_VENDOR_ID_NEC, 'int'),
                    'usb_device.product_id': (self.USB_PROD_ID_NEC_HUB,
                                              'int'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {'devices': devices,
                    },
                },
            }

        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)

        # The PCI-USB bridge is a child of the system.
        root_device = parser.hal_devices[self.UDI_COMPUTER]
        pci_usb_bridge = parser.hal_devices[self.UDI_USB_CONTROLLER_PCI_SIDE]
        self.assertEqual(root_device.getRealChildren(), [pci_usb_bridge],
                         'Unexpected list of real children of the root '
                         'device')

        # The "output aspect" of the PCI->USB bridge and the node for
        # raw USB access do not appear as childs of the PCI->USB bridge,
        # but the node for the USB device is considered to be a child
        # of the bridge.

        usb_device = parser.hal_devices[self.UDI_USB_HUB]
        self.assertEqual(pci_usb_bridge.getRealChildren(), [usb_device],
                         'Unexpected list of real children of the PCI-> '
                         'USB bridge')


class TestHALDeviceUSBDevices(TestCaseHWDB):
    """Tests for HALDevice.is_real_device: USB devices."""

    def setUp(self):
        """Setup the test environment."""
        super(TestHALDeviceUSBDevices, self).setUp()
        self.usb_controller_pci_side = {
            'id': 1,
            'udi': self.UDI_USB_CONTROLLER_PCI_SIDE,
            'properties': {
                'info.bus': ('pci', 'str'),
                'pci.device_class': (PCI_CLASS_SERIALBUS_CONTROLLER, 'int'),
                'pci.device_subclass': (PCI_SUBCLASS_SERIALBUS_USB, 'int'),
                },
            }
        self.usb_controller_usb_side = {
            'id': 2,
            'udi': self.UDI_USB_CONTROLLER_USB_SIDE,
            'properties': {
                'info.parent': (self.UDI_USB_CONTROLLER_PCI_SIDE, 'str'),
                'info.bus': ('usb_device', 'str'),
                'usb_device.vendor_id': (0, 'int'),
                'usb_device.product_id': (0, 'int'),
                },
            }
        self.usb_storage_device = {
            'id': 3,
            'udi': self.UDI_USB_STORAGE,
            'properties': {
                'info.parent': (self.UDI_USB_CONTROLLER_USB_SIDE, 'str'),
                'info.bus': ('usb_device', 'str'),
                'usb_device.vendor_id': (self.USB_VENDOR_ID_USBEST, 'int'),
                'usb_device.product_id': (self.USB_PROD_ID_USBBEST_MEMSTICK,
                                          'int'),
                },
            }
        self.parsed_data = {
            'hardware': {
                'hal': {
                    'devices': [
                        self.usb_controller_pci_side,
                        self.usb_controller_usb_side,
                        self.usb_storage_device,
                        ],
                    },
                },
            }

    def assertWarningMessage(self, submission_key, log_message):
        """Search for message in the log entries for submission_key.

        :raise: AssertionError if no log message exists that starts with
            "Parsing submission <submission_key>:" and that contains
            the text passed as the parameter message.
        """
        expected_message = ('Parsing submission %s: %s'
                            % (submission_key, log_message))
        last_log_messages = []
        for record in self.handler.records:
            if record.levelno != logging.WARNING:
                continue
            candidate = record.getMessage()
            if candidate == expected_message:
                return
        raise AssertionError('No log message found: %s' % expected_message)

    def testUSBDeviceRegularCase(self):
        """Test of HALDevice.is_real_device: info.bus == 'usb_device'."""
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(self.parsed_data)
        device = parser.hal_devices[self.UDI_USB_STORAGE]
        self.failUnless(device.is_real_device,
                        'Regular USB Device not treated as a real device.')

    def testUSBHostController(self):
        """Test of HALDevice.is_real_device: info.bus == 'usb_device'.

        Special case: vendor ID and product ID of the device are zero;
        the parent device is a PCI/USB host controller.
        """

        parser = SubmissionParser(self.log)
        parser.buildDeviceList(self.parsed_data)
        device = parser.hal_devices[self.UDI_USB_CONTROLLER_USB_SIDE]
        self.failIf(device.is_real_device,
                    'USB Device with vendor/product ID 0:0 property '
                    'treated as a real device.')

    def testUSBHostControllerInvalidParentClass(self):
        """Test of HALDevice.is_real_device: info.bus == 'usb_device'.

        Special case: vendor ID and product ID of the device are zero;
        the parent device cannot be identified as a PCI/USB host
        controller: Wrong PCI device class of the parent device.
        """
        parent_properties = self.usb_controller_pci_side['properties']
        parent_properties['pci.device_class'] = (PCI_CLASS_STORAGE, 'int')
        parser = SubmissionParser(self.log)
        parser.submission_key = 'USB device test 1'
        parser.buildDeviceList(self.parsed_data)
        device = parser.hal_devices[self.UDI_USB_CONTROLLER_USB_SIDE]
        self.failIf(device.is_real_device,
                    'USB Device with vendor/product ID 0:0 property '
                    'treated as a real device.')
        self.assertWarningMessage(
            parser.submission_key,
            'USB device found with vendor ID==0, product ID==0, where the '
            'parent device does not look like a USB host controller: '
            + self.UDI_USB_CONTROLLER_USB_SIDE)

    def testUSBHostControllerInvalidParentSubClass(self):
        """Test of HALDevice.is_real_device: info.bus == 'usb_device'.

        Special case: vendor ID and product ID of the device are zero;
        the parent device cannot be identified as a PCI/USB host
        controller: Wrong PCI device subclass of the parent device.
        """
        parent_properties = self.usb_controller_pci_side['properties']
        parent_properties['pci.device_subclass'] = (1, 'int')
        parser = SubmissionParser(self.log)
        parser.submission_key = 'USB device test 2'
        parser.buildDeviceList(self.parsed_data)
        device = parser.hal_devices[self.UDI_USB_CONTROLLER_USB_SIDE]
        self.failIf(device.is_real_device,
                    'USB Device with vendor/product ID 0:0 property '
                    'treated as a real device.')
        self.assertWarningMessage(
            parser.submission_key,
            'USB device found with vendor ID==0, product ID==0, where the '
            'parent device does not look like a USB host controller: '
            +  self.UDI_USB_CONTROLLER_USB_SIDE)

    def testUSBHostControllerUnexpectedParentBus(self):
        """Test of HALDevice.is_real_device: info.bus == 'usb_device'.

        Special case: vendor ID and product ID of the device are zero;
        the parent device cannot be identified as a PCI/USB host
        controller: Wrong bus of the parent device.
        """
        parent_properties = self.usb_controller_pci_side['properties']
        parent_properties['info.bus'] = ('not pci', 'str')
        parser = SubmissionParser(self.log)
        parser.submission_key = 'USB device test 3'
        parser.buildDeviceList(self.parsed_data)
        device = parser.hal_devices[self.UDI_USB_CONTROLLER_USB_SIDE]
        self.failIf(device.is_real_device,
                    'USB Device with vendor/product ID 0:0 property '
                    'treated as a real device.')
        self.assertWarningMessage(
            parser.submission_key,
            'USB device found with vendor ID==0, product ID==0, where the '
            'parent device does not look like a USB host controller: '
            + self.UDI_USB_CONTROLLER_USB_SIDE)

        # All other devices which have an info.bus property return True
        # for HALDevice.is_real_device. The USB host controller in the
        # test data is an example.
        device = parser.hal_devices[self.UDI_USB_CONTROLLER_PCI_SIDE]
        self.failUnless(device.is_real_device,
                        'Device with existing info.bus property not treated '
                        'as a real device.')

    def testHALDeviceVendorFromInfoVendor(self):
        """Test of HALDevice.vendor, regular case.

        The value is copied from info.vendor, if available."""
        devices = [
            {
                'id': 1,
                'udi': self.UDI_SATA_CONTROLLER,
                'properties': {
                    'info.bus': ('pci', 'str'),
                    'info.vendor': ('Intel Corporation', 'str'),
                    'pci.vendor': ('should not be used', 'str'),
                    }
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_vendor = parser.hal_devices[self.UDI_SATA_CONTROLLER].vendor
        self.assertEqual(found_vendor, 'Intel Corporation',
                         'Unexpected result of HWDevice.vendor. '
                         'Expected Intel Corporation, got %r.'
                         % found_vendor)

    def testHALDeviceVendorFromBusVendor(self):
        """Test of HALDevice.vendor, value copied from ${bus}.vendor.

        If the property info.vendor does not exist, ${bus}.vendor
        is tried.
        """
        devices = [
            {
                'id': 1,
                'udi': self.UDI_SATA_CONTROLLER,
                'properties': {
                    'info.bus': ('pci', 'str'),
                    'pci.vendor': ('Intel Corporation', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_vendor = parser.hal_devices[self.UDI_SATA_CONTROLLER].vendor
        self.assertEqual(found_vendor, 'Intel Corporation',
                         'Unexpected result of HWDevice.vendor, '
                         'if info.vendor does not exist. '
                         'Expected Intel Corporation, got %r.'
                         % found_vendor)

    def testHALDeviceVendorScsi(self):
        """Test of HALDevice.vendor for SCSI devices: regular case."""
        devices = [
            {
                'id': 1,
                'udi': self.UDI_SCSI_DISK,
                'properties': {
                    'info.bus': ('scsi', 'str'),
                    'scsi.vendor': ('SEAGATE', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_vendor = parser.hal_devices[self.UDI_SCSI_DISK].vendor
        self.assertEqual(found_vendor, 'SEAGATE',
                         'Unexpected result of HWDevice.vendor '
                         'for SCSI device. Expected SEAGATE, got %r.'
                         % found_vendor)

    def testHALDeviceVendorScsiAta(self):
        """Test of HALDevice.vendor for SCSI devices: fake IDE/SATA disks."""
        devices = [
            {
                'id': 1,
                'udi': self.UDI_SCSI_DISK,
                'properties': {
                    'info.bus': ('scsi', 'str'),
                    'scsi.vendor': ('ATA', 'str'),
                    'scsi.model': ('Hitachi HTS54161', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_vendor = parser.hal_devices[self.UDI_SCSI_DISK].vendor
        self.assertEqual(found_vendor, 'Hitachi',
                         'Unexpected result of HWDevice.vendor, for fake '
                         'SCSI device. Expected Hitachi, got %r.'
                         % found_vendor)

    def testHALDeviceVendorSystem(self):
        """Test of HALDevice.vendor for the machine itself."""
        # HAL does not provide info.vendor for the root UDI
        # /org/freedesktop/Hal/devices/computer, hence HALDevice.vendor
        # reads the vendor name from system.vendor
        devices = [
            {
                'id': 1,
                'udi': self.UDI_COMPUTER,
                'properties': {
                    'info.bus': ('unknown', 'str'),
                    'system.vendor': ('FUJITSU SIEMENS', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_vendor = parser.hal_devices[self.UDI_COMPUTER].vendor
        self.assertEqual(found_vendor, 'FUJITSU SIEMENS',
                         'Unexpected result of HWDevice.vendor for a '
                         'system. Expected FUJITSU SIEMENS, got %r.'
                         % found_vendor)

    def testHALDeviceProductFromInfoProduct(self):
        """Test of HALDevice.product, regular case.

        The value is copied from info.product, if available."""
        # The product name is copied from the HAL property info.product,
        # if it is avaliable.
        devices = [
             {
                'id': 1,
                'udi': self.UDI_SATA_CONTROLLER,
                'properties': {
                    'info.bus': ('pci', 'str'),
                    'info.product': ('82801GBM/GHM SATA AHCI Controller',
                                     'str'),
                    'pci.product': ('should not be used', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_product = parser.hal_devices[self.UDI_SATA_CONTROLLER].product
        self.assertEqual(found_product, '82801GBM/GHM SATA AHCI Controller',
                         'Unexpected result of HWDevice.product. '
                         'Expected 82801GBM/GHM SATA AHCI Controller, got %r.'
                         % found_product)

    def testHALDeviceProductFromBusProduct(self):
        """Test of HALDevice.product, value copied from ${bus}.product.

        If the property info.product does not exist, ${bus}.product
        """
        devices = [
            {
                'id': 1,
                'udi': self.UDI_SATA_CONTROLLER,
                'properties': {
                    'info.bus': ('pci', 'str'),
                    'pci.product': ('82801GBM/GHM SATA AHCI Controller',
                                    'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_product = parser.hal_devices[self.UDI_SATA_CONTROLLER].product
        self.assertEqual(found_product, '82801GBM/GHM SATA AHCI Controller',
                         'Unexpected result of HWDevice.product, '
                         'if info.product does not exist. '
                         'Expected 82801GBM/GHM SATA AHCI Controller, got %r.'
                         % found_product)

    def testHALDeviceProductScsi(self):
        """Test of HALDevice.product for SCSI devices: regular case."""
        # The name of SCSI device is copied from the property scsi.model.
        devices = [
            {
                'id': 1,
                'udi': self.UDI_SCSI_DISK,
                'properties': {
                    'info.bus': ('scsi', 'str'),
                    'scsi.vendor': ('SEAGATE', 'str'),
                    'scsi.model': ('ST36530N', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_product = parser.hal_devices[self.UDI_SCSI_DISK].product
        self.assertEqual(found_product, 'ST36530N',
                         'Unexpected result of HWDevice.product '
                         'for SCSI device. Expected ST36530N, got %r.'
                         % found_product)

    def testHALDeviceProductScsiAta(self):
        """Test of HALDevice.product for SCSI devices: fake IDE/SATA disks."""
        devices = [
            {
                'id': 1,
                'udi': self.UDI_SCSI_DISK,
                'properties': {
                    'info.bus': ('scsi', 'str'),
                    'scsi.vendor': ('ATA', 'str'),
                    'scsi.model': ('Hitachi HTS54161', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_product = parser.hal_devices[self.UDI_SCSI_DISK].product
        self.assertEqual(found_product, 'HTS54161',
                         'Unexpected result of HWDevice.product, for fake '
                         'SCSI device. Expected HTS54161, got %r.'
                         % found_product)

    def testHALDeviceProductSystem(self):
        """Test of HALDevice.product for the machine itself."""
        # HAL sets info.product to "Computer" for the root UDI
        # /org/freedesktop/Hal/devices/computer, hence HALDevice.product
        # reads the product name from system.product.
        devices = [
            {
                'id': 1,
                'udi': self.UDI_COMPUTER,
                'properties': {
                    'info.bus': ('unknown', 'str'),
                    'system.product': ('LIFEBOOK E8210', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_product = parser.hal_devices[self.UDI_COMPUTER].product
        self.assertEqual(found_product, 'LIFEBOOK E8210',
                         'Unexpected result of HWDevice.product, '
                         'if info.product does not exist. '
                         'Expected LIFEBOOK E8210, got %r.'
                         % found_product)

    def testHALDeviceVendorId(self):
        """Test of HALDevice.vendor_id.

        Many buses have a numerical vendor ID. Except for the special
        cases tested below, HWDevice.vendor_id returns the HAL property
        ${bus}.vendor_id.
        """
        devices = [
             {
                'id': 1,
                'udi': self.UDI_SATA_CONTROLLER,
                'properties': {
                    'info.bus': ('pci', 'str'),
                    'pci.vendor_id': (self.PCI_VENDOR_ID_INTEL, 'int'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_vendor_id = parser.hal_devices[
            self.UDI_SATA_CONTROLLER].vendor_id
        self.assertEqual(found_vendor_id, self.PCI_VENDOR_ID_INTEL,
                         'Unexpected result of HWDevice.vendor_id. '
                         'Expected 0x8086, got 0x%x.'
                         % found_vendor_id)

    def testHALDeviceVendorIdScsi(self):
        """Test of HALDevice.vendor_id for SCSI devices.

        The SCSI specification does not know about a vendor ID,
        we use the vendor string as returned by INQUIRY command
        as the ID.
        """
        devices = [
            {
                'id': 1,
                'udi': self.UDI_SCSI_DISK,
                'properties': {
                    'info.bus': ('scsi', 'str'),
                    'scsi.vendor': ('SEAGATE', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_vendor_id = parser.hal_devices[self.UDI_SCSI_DISK].vendor_id
        self.assertEqual(found_vendor_id, 'SEAGATE',
                         'Unexpected result of HWDevice.vendor_id for a. '
                         'SCSI device. Expected SEAGATE, got %r.'
                         % found_vendor_id)

    def testHALDeviceVendorIdScsiAta(self):
        """Test of HALDevice.vendor_id for SCSI devices: fake IDE/SATA disks.
        """
        devices = [
            {
                'id': 1,
                'udi': self.UDI_SCSI_DISK,
                'properties': {
                    'info.bus': ('scsi', 'str'),
                    'scsi.vendor': ('ATA', 'str'),
                    'scsi.model': ('Hitachi HTS54161', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_vendor_id = parser.hal_devices[self.UDI_SCSI_DISK].vendor_id
        self.assertEqual(found_vendor_id, 'Hitachi',
                         'Unexpected result of HWDevice.vendor_id for a. '
                         'fake SCSI device. Expected Hitachi, got %r.'
                         % found_vendor_id)

    def testHALDeviceVendorIdSystem(self):
        """Test of HALDevice.vendor_id for the machine itself."""
        # HAL does not provide the property info.vendor_id for the
        # root UDI /org/freedesktop/Hal/devices/computer. We use
        # HALDevice.vendor instead.
        devices = [
            {
                'id': 1,
                'udi': self.UDI_COMPUTER,
                'properties': {
                    'info.bus': ('unknown', 'str'),
                    'system.vendor': ('FUJITSU SIEMENS', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_vendor_id = parser.hal_devices[self.UDI_COMPUTER].vendor_id
        self.assertEqual(found_vendor_id, 'FUJITSU SIEMENS',
                         'Unexpected result of HWDevice.vendor_id for a '
                         'system. Expected FUJITSU SIEMENS, got %r.'
                         % found_vendor_id)

    def testHALDeviceProductId(self):
        """Test of HALDevice.product_id.

        Many buses have a numerical product ID. Except for the special
        cases tested below, HWDevice.product_id returns the HAL property
        ${bus}.product_id.
        """
        devices = [
             {
                'id': 1,
                'udi': self.UDI_SATA_CONTROLLER,
                'properties': {
                    'info.bus': ('pci', 'str'),
                    'pci.product_id': (0x27c5, 'int'),
                    },
                },
             ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_product_id = parser.hal_devices[
            self.UDI_SATA_CONTROLLER].product_id
        self.assertEqual(found_product_id, 0x27c5,
                         'Unexpected result of HWDevice.product_id. '
                         'Expected 0x27c5, got 0x%x.'
                         % found_product_id)

    def testHALDeviceProductIdScsi(self):
        """Test of HALDevice.product_id for SCSI devices.

        The SCSI specification does not know about a product ID,
        we use the product string as returned by INQUIRY command
        as the ID.
        """
        devices = [
            {
                'id': 1,
                'udi': self.UDI_SCSI_DISK,
                'properties': {
                    'info.bus': ('scsi', 'str'),
                    'scsi.vendor': ('SEAGATE', 'str'),
                    'scsi.model': ('ST36530N', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {'devices': devices,
                    }
                }
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_product_id = parser.hal_devices[self.UDI_SCSI_DISK].product_id
        self.assertEqual(found_product_id, 'ST36530N',
                         'Unexpected result of HWDevice.product_id for a. '
                         'SCSI device. Expected ST35630N, got %r.'
                         % found_product_id)

    def testHALDeviceProductIdScsiAta(self):
        """Test of HALDevice.product_id for SCSI devices: fake IDE/SATA disks.
        """
        devices = [
            {
                'id': 1,
                'udi': self.UDI_SCSI_DISK,
                'properties': {
                    'info.bus': ('scsi', 'str'),
                    'scsi.vendor': ('ATA', 'str'),
                    'scsi.model': ('Hitachi HTS54161', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_product_id = parser.hal_devices[self.UDI_SCSI_DISK].product_id
        self.assertEqual(found_product_id, 'HTS54161',
                         'Unexpected result of HWDevice.product_id for a. '
                         'fake SCSI device. Expected HTS54161, got %r.'
                         % found_product_id)

    def testHALDeviceProductIdSystem(self):
        """Test of HALDevice.product_id for the machine itself."""
        # HAL does not provide info.product_id for the root UDI
        # /org/freedesktop/Hal/devices/computer. We use
        # HALDevice.product instead.
        devices = [
            {
                'id': 1,
                'udi': self.UDI_COMPUTER,
                'properties': {
                    'info.bus': ('unknown', 'str'),
                    'system.product': ('LIFEBOOK E8210', 'str'),
                    },
                },
            ]
        parsed_data = {
            'hardware': {
                'hal': {
                    'devices': devices,
                    },
                },
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        found_product_id = parser.hal_devices[self.UDI_COMPUTER].product_id
        self.assertEqual(found_product_id, 'LIFEBOOK E8210',
                         'Unexpected result of HWDevice.product_id for a '
                         'system. Expected LIFEBOOK E8210, got %r.'
                         % found_product_id)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
