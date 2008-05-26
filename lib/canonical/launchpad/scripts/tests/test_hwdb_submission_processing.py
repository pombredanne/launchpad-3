# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Tests of the HWDB submissions parser."""

import logging
from unittest import TestCase, TestLoader

from zope.testing.loghandler import Handler

from canonical.launchpad.interfaces.hwdb import HWBus
from canonical.launchpad.scripts.hwdbsubmissions import (
    HALDevice, SubmissionParser)
from canonical.testing import BaseLayer


class TestHWDBSubmissionProcessing(TestCase):
    """Tests for the HWDB submission processing."""

    layer = BaseLayer

    UDI_COMPUTER = '/org/freedesktop/Hal/devices/computer'
    UDI_SATA_CONTOLLER = '/org/freedesktop/Hal/devices/pci_8086_27c5'
    UDI_SATA_CONTOLLER_SCSI = ('/org/freedesktop/Hal/devices/'
                               'pci_8086_27c5_scsi_host')
    UDI_SATA_DISK = ('org/freedesktop/Hal/devices/'
                     'pci_8086_27c5_scsi_host_scsi_device_lun0')
    UDI_USB_STORAGE = '/org/freedesktop/Hal/devices/usb_device_1307_163_07'
    UDI_USB_STORAGE_IF0 = ('/org/freedesktop/Hal/devices/'
                           'usb_device_1307_163_07_if0')
    UDI_USB_STORAGE_SCSI_HOST = ('/org/freedesktop/Hal/devices/'
                                 'usb_device_1307_163_07_if0scsi_host')
    UDI_USB_STORAGE_SCSI_DEVICE = ('/org/freedesktop/Hal/devices/'
                                   'usb_device_1307_163_07_if0'
                                   'scsi_host_scsi_device_lun0')
    UDI_PCI_PCI_BRIDGE = '/org/freedesktop/Hal/devices/pci_8086_2448'
    UDI_PCI_PCCARD_BRIDGE = '/org/freedesktop/Hal/devices/pci_1217_7134'
    UDI_PCCARD_DEVICE = '/org/freedesktop/Hal/devices/pci_9004_6075'
    def setUp(self):
        """Setup the test environment."""
        self.log = logging.getLogger('test_hwdb_submission_parser')
        self.log.setLevel(logging.INFO)
        self.handler = Handler(self)
        self.handler.add(self.log.name)

    def assertWarningMessage(self, submission_key, log_message):
        """Search for message in the log entries for submission_key.

        assertWarningMessage requires that
        (a) a log message starts with "Parsing submisson <submission_key>:"
        (b) the error message passed as the parameter message appears
            in a log string that matches (a)

        If both criteria match, assertErrormessage does not raise any
        exception.
        """
        expected_message = ('Parsing submission %s: %s'
                            % (submission_key, log_message))
        last_log_messages = []
        for r in self.handler.records:
            if r.levelno != logging.WARNING:
                continue
            candidate = r.getMessage()
            if candidate == expected_message:
                return
        raise AssertionError('No log message found: %s' % expected_message)

    def testBuildDeviceList(self):
        """Test the creation of list HALDevice instances for a submission."""
        devices = [
            {'id': 1,
             'udi': self.UDI_COMPUTER,
             'properties': {}
            },
            {'id': 2,
             'udi': self.UDI_SATA_CONTOLLER,
             'properties': {
                 'info.parent': (self.UDI_COMPUTER, 'str'),
                 },
            }
            ]
        parsed_data = {
            'hardware': {
                'hal': {'devices': devices,
                    }
                }
            }
        parser = SubmissionParser(self.log)
        parser.buildDeviceList(parsed_data)
        self.assertEqual(len(parser.hal_devices), len(devices),
                         'Numbers of devices in parser.hal_devices and in '
                         'sample data are different')
        root_device = parser.hal_devices[self.UDI_COMPUTER]
        self.assertEqual(root_device.id, 1,
                         'Unexpected value of root device ID')
        self.assertEqual(root_device.udi, self.UDI_COMPUTER,
                         'Unexpected value of root device UDI')
        self.assertEqual(root_device.properties,
                         devices[0]['properties'],
                         'Unexpected properties of root device')
        child_device = parser.hal_devices[self.UDI_SATA_CONTOLLER]
        self.assertEqual(child_device.id, 2,
                         'Unexpected value of child device ID')
        self.assertEqual(child_device.udi, self.UDI_SATA_CONTOLLER,
                         'Unexpected value of child device UDI')
        self.assertEqual(child_device.properties,
                         devices[1]['properties'],
                         'Unexpected properties of child device')

        parent = parser.hal_devices[self.UDI_COMPUTER]
        child = parser.hal_devices[self.UDI_SATA_CONTOLLER]
        self.assertEqual(parent.children, [child],
                         'Child missing in parent.children')
        self.assertEqual(child.parent, parent,
                         'Invalid value of child.parent')

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
                {'id': 1,
                 'udi': UDI_TEST_DEVICE,
                 'properties': {
                     'info.bus': (hal_bus, 'str'),
                     }
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
            test_device = parser.hal_devices[UDI_TEST_DEVICE]
            test_bus = test_device.getBus()
            self.assertEqual(test_bus, real_bus,
                             'Unexpected result of HALDevice.getBus for '
                             'HAL bus %s: %s' % (hal_bus, test_bus.title))

    def testHALDeviceGetBusSystem(self):
        """Test of HALDevice.getBus, for the tested machine itself."""

        devices = [
            {'id': 1,
             'udi': self.UDI_COMPUTER,
             'properties': {
                 'info.bus': ('unknown', 'str'),
                 }
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
            {'id': 1,
             'udi': self.UDI_USB_STORAGE,
             'properties': {
                 'info.bus': ('usb_device', 'str'),
                 }
            },
            # The storage interface of the USB device.
            {'id': 2,
             'udi': self.UDI_USB_STORAGE_IF0,
             'properties': {
                 'info.bus': ('usb', 'str'),
                 'info.parent': (self.UDI_USB_STORAGE, 'str'),
                 }
            },
            # The fake SCSI host of the storage device. Note that HAL does
            # _not_ provide the info.bus property.
            {'id': 3,
             'udi': self.UDI_USB_STORAGE_SCSI_HOST,
             'properties': {
                 'info.parent': (self.UDI_USB_STORAGE_IF0, 'str'),
                 }
            },
            # The fake SCSI disk.
            {'id': 3,
             'udi': self.UDI_USB_STORAGE_SCSI_DEVICE,
             'properties': {
                 'info.bus': ('scsi', 'str'),
                 'info.parent': (self.UDI_USB_STORAGE_SCSI_HOST, 'str'),
                 }
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
            {'id': 1,
             'udi': self.UDI_SATA_CONTOLLER,
             'properties': {
                 'info.bus': ('pci', 'str'),
                 'pci.device_class': (1, 'int'),
                 'pci.device_subclass': (6, 'int'),
                 }
            },
            # The fake SCSI host of the storage device. Note that HAL does
            # _not_ provide the info.bus property.
            {'id': 2,
             'udi': self.UDI_SATA_CONTOLLER_SCSI,
             'properties': {
                 'info.parent': (self.UDI_SATA_CONTOLLER, 'str'),
                 }
            },
            # The (possibly fake) SCSI disk.
            {'id': 3,
             'udi': self.UDI_SATA_DISK,
             'properties': {
                 'info.bus': ('scsi', 'str'),
                 'info.parent': (self.UDI_SATA_CONTOLLER_SCSI, 'str'),
                 }
            },
            ]
        parsed_data = {
            'hardware': {
                'hal': {'devices': devices,
                    }
                }
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
                'class device, subclass %i: %r' % (device_subclass,
                                                   found_bus))

    def testHALDeviceGetBusPci(self):
        """Test of HALDevice.getBus for info.bus=='pci'.

        If info.bus == 'pci', we may have a real PCI device or a PCCard.
        """
        # possible parent device for the tested device,
        parent_devices = [
            # The host itself.
            {'id': 1,
             'udi': self.UDI_COMPUTER,
             'properties': {
                 'info.bus': ('unknown', 'str'),
                 }
            },
            # A PCI->PCI bridge
            {'id': 2,
             'udi': self.UDI_PCI_PCI_BRIDGE,
             'properties': {
                 'info.parent': (self.UDI_COMPUTER, 'str'),
                 'info.bus': ('pci', 'str'),
                 'pci.device_class': (6, 'int'),
                 'pci.device_subclass': (4, 'int'),
                 }
            },
            # A PCI->PCCard bridge
            {'id': 3,
             'udi': self.UDI_PCI_PCCARD_BRIDGE,
             'properties': {
                 'info.parent': (self.UDI_PCI_PCI_BRIDGE, 'str'),
                 'info.bus': ('pci', 'str'),
                 'pci.device_class': (6, 'int'),
                 'pci.device_subclass': (7, 'int'),
                 }
            },
        ]
        tested_device = {
            'id': 4,
            'udi': self.UDI_PCCARD_DEVICE,
            'properties': {
                'info.bus': ('pci', 'str'),
                }
            }
        parsed_data = {
            'hardware': {
                'hal': {}
                }
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
            {'id': 1,
             'udi': self.UDI_PCCARD_DEVICE,
             'properties': {
                 'info.bus': ('nonsense', 'str'),
                 }
            },
            ]
        parsed_data = {
            'hardware': {
                'hal': {'devices': devices,
                    }
                }
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


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
