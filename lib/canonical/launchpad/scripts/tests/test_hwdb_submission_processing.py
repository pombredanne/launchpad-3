# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Tests of the HWDB submissions parser."""

import logging
from unittest import TestCase, TestLoader

from zope.testing.loghandler import Handler

from canonical.launchpad.interfaces import HWBus
from canonical.launchpad.scripts.hwdbsubmissions import (
    HALDevice, SubmissionParser)
from canonical.testing import BaseLayer


class TestHWDBSubmissionProcessing(TestCase):
    """Tests of the HWDB submission processing."""

    layer = BaseLayer

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
             'udi': '/org/freedesktop/Hal/devices/computer',
             'properties': {}
            },
            {'id': 2,
             'udi': '/org/freedesktop/Hal/devices/pci_8086_27c5',
             'properties': {
                 'info.parent': ('/org/freedesktop/Hal/devices/computer',
                                 'str'),
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
        root_device = parser.hal_devices[
            '/org/freedesktop/Hal/devices/computer']
        self.assertEqual(root_device.id, 1,
                         'Unexpected value of root device ID')
        self.assertEqual(root_device.udi,
                         '/org/freedesktop/Hal/devices/computer',
                         'Unexpected value of root device UDI')
        self.assertEqual(root_device.properties,
                         devices[0]['properties'],
                         'Unexpected properties of root device')
        child_device = parser.hal_devices[
            '/org/freedesktop/Hal/devices/pci_8086_27c5']
        self.assertEqual(child_device.id, 2,
                         'Unexpected value of child device ID')
        self.assertEqual(child_device.udi,
                         '/org/freedesktop/Hal/devices/pci_8086_27c5',
                         'Unexpected value of child device UDI')
        self.assertEqual(child_device.properties,
                         devices[1]['properties'],
                         'Unexpected properties of child device')

        parent = parser.hal_devices['/org/freedesktop/Hal/devices/computer']
        child = parser.hal_devices[
            '/org/freedesktop/Hal/devices/pci_8086_27c5']
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
        
        For most busses as "seen" by HAL, HALDevice.getBus returns a
        unique HWBus value.
        """
        for hal_bus, real_bus in (('usb_device', HWBus.USB),
                                  ('pcmcia', HWBus.PCMCIA),
                                  ('ide', HWBus.IDE),
                                  ('serio', HWBus.SERIAL),
                                 ):
            devices = [
                {'id': 1,
                 'udi': '/org/freedesktop/Hal/devices/test_device',

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
            test_device = parser.hal_devices[
                '/org/freedesktop/Hal/devices/test_device']
            test_bus = test_device.getBus()
            self.assertEqual(test_bus, real_bus,
                             'Unexpected result of HALDevice.getBus for '
                             'HAL bus %s: %s' % (hal_bus, test_bus.title))

    def testHALDeviceGetBusSystem(self):
        """Test of HALDevice.getBus, for the tested machine itself."""

        devices = [
            {'id': 1,
             'udi': '/org/freedesktop/Hal/devices/computer',

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
        test_device = parser.hal_devices[
            '/org/freedesktop/Hal/devices/computer']
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
             'udi': '/org/freedesktop/Hal/devices/usb_device_1307_163_07',
             'properties': {
                 'info.bus': ('usb_device', 'str'),
                 }
            },
            # The storage interface of the USB device.
            {'id': 2,
             'udi': '/org/freedesktop/Hal/devices/usb_device_1307_163_07_if0',
             'properties': {
                 'info.bus': ('usb', 'str'),
                 'info.parent': ('/org/freedesktop/Hal/devices/'
                                 'usb_device_1307_163_07', 'str'),
                 }
            },
            # The fake SCSI host of the storage device. Note that HAL does
            # _not_ provide the info.bus property.
            {'id': 3,
             'udi': '/org/freedesktop/Hal/devices/usb_device_1307_163_07_if0'
                    'scsi_host',
             'properties': {
                 'info.parent': ('/org/freedesktop/Hal/devices/'
                                 'usb_device_1307_163_07_if0', 'str'),
                 }
            },
            # The fake SCSI disk.
            {'id': 3,
             'udi': '/org/freedesktop/Hal/devices/usb_device_1307_163_07_if0'
                    'scsi_host_scsi_device_lun0',
             'properties': {
                 'info.bus': ('scsi', 'str'),
                 'info.parent': ('/org/freedesktop/Hal/devices/'
                                     'usb_device_1307_163_07_if0scsi_host',
                                 'str'),
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
            '/org/freedesktop/Hal/devices/usb_device_1307_163_07_if0'
            'scsi_host_scsi_device_lun0']
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
             'udi': '/org/freedesktop/Hal/devices/pci_8086_27c5',
             'properties': {
                 'info.bus': ('pci', 'str'),
                 'pci.device_class': (1, 'int'),
                 'pci.device_subclass': (6, 'int'),
                 }
            },
            # The fake SCSI host of the storage device. Note that HAL does
            # _not_ provide the info.bus property.
            {'id': 3,
             'udi': '/org/freedesktop/Hal/devices/pci_8086_27c5_scsi_host',
             'properties': {
                 'info.parent': ('/org/freedesktop/Hal/devices/pci_8086_27c5',
                                 'str'),
                 }
            },
            # The (possibly fake) SCSI disk.
            {'id': 3,
             'udi':'org/freedesktop/Hal/devices/'
                   'pci_8086_27c5_scsi_host_scsi_device_lun0',
             'properties': {
                 'info.bus': ('scsi', 'str'),
                 'info.parent': ('/org/freedesktop/Hal/devices/'
                                 'pci_8086_27c5_scsi_host', 'str'),
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
            fake_scsi_disk = parser.hal_devices[
                'org/freedesktop/Hal/devices/pci_8086_27c5_scsi_host'
                '_scsi_device_lun0']
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
             'udi': '/org/freedesktop/Hal/devices/computer',
             'properties': {
                 'info.bus': ('unknown', 'str'),
                 }
            },
            # A PCI->PCI bridge
            {'id': 2,
             'udi': '/org/freedesktop/Hal/devices/pci_8086_2448',
             'properties': {
                 'info.parent': ('/org/freedesktop/Hal/devices/computer',
                                 'str'),
                 'info.bus': ('pci', 'str'),
                 'pci.device_class': (6, 'int'),
                 'pci.device_subclass': (4, 'int'),
                 }
            },
            # A PCI->PCCard bridge
            {'id': 3,
             'udi': '/org/freedesktop/Hal/devices/pci_1217_7134',
             'properties': {
                 'info.parent': ('/org/freedesktop/Hal/devices/computer',
                                 'str'),
                 'info.bus': ('pci', 'str'),
                 'pci.device_class': (6, 'int'),
                 'pci.device_subclass': (7, 'int'),
                 }
            },
        ]
        tested_device = {
            'id': 4,
            'udi': '/org/freedesktop/Hal/devices/pci_9004_6075',
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
            '/org/freedesktop/Hal/devices/computer': HWBus.PCI,
            '/org/freedesktop/Hal/devices/pci_8086_2448': HWBus.PCI,
            '/org/freedesktop/Hal/devices/pci_1217_7134': HWBus.PCCARD,
            }

        parser = SubmissionParser(self.log)

        for parent_device in parent_devices:
            devices = parent_devices[:]
            tested_device['properties']['info.parent'] = (
                parent_device['udi'], 'str')
            devices.append(tested_device)
            parsed_data['hardware']['hal']['devices'] = devices
            parser.buildDeviceList(parsed_data)
            tested_hal_device = parser.hal_devices[
                '/org/freedesktop/Hal/devices/pci_9004_6075']
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
             'udi': '/org/freedesktop/Hal/devices/pci_9004_6075',
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
        found_bus = parser.hal_devices[
            '/org/freedesktop/Hal/devices/pci_9004_6075'].getBus()
        self.assertEqual(found_bus, None,
                         'Unexpected result of HWDevice.getBus for an '
                         'unknown bus name: Expected None, got %r.'
                         % found_bus)
        self.assertWarningMessage(
            parser.submission_key,
            "Unknown bus 'nonsense' for device "
            "/org/freedesktop/Hal/devices/pci_9004_6075")


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
