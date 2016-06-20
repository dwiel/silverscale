#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hid
import time
from silverscale.usb_ids import SUPPORTED_DEVICES

SCALE_CLASSES = {
    0x1: 'Scale Class I Metric',
    0x2: 'Scale Class I Metric',
    0x3: 'Scale Class II Metric',
    0x4: 'Scale Class III Metric',
    0x5: 'Scale Class IIIL Metric',
    0x6: 'Scale Class IV Metric',
    0x7: 'Scale Class III English',
    0x8: 'Scale Class IIIL English',
    0x9: 'Scale Class IV English',
    0xA: 'Scale Class Generic',
    0xB: 'Reserved (0x2B)',
    0xC: 'Reserved (0x2C)',
    0xD: 'Reserved (0x2D)',
    0xE: 'Reserved (0x2E)',
    0xF: 'Reserved (0x2F)'
}

WEIGHT_UNITS = {
    0x0: 'units',  # Unknown Units
    0x1: 'mg',     # Milligrams
    0x2: 'g',      # Grams
    0x3: 'kg',     # Kilograms
    0x4: 'ct',     # Carats
    0x5: 'taels',  # Taels
    0x6: 'gr',     # Grains
    0x7: 'dwt',    # Pennyweights
    0x8: 'tonnes', # Metric Tons
    0x9: 'tons',   # Avoir Tons
    0xA: 'ozt',    # Troy Ounces
    0xB: 'oz',     # Ounces
    0xC: 'lbs'     # Pounds
}

SCALE_STATUSES = {
    0x00: 'Unknown Status',
    0x01: 'Fault',
    0x02: 'Stable at Center of Zero',
    0x03: 'In Motion',
    0x04: 'Weight Stable',
    0x05: 'Under Zero',
    0x06: 'Over Weight Limit',
    0x07: 'Requires Calibration',
    0x08: 'Requires Re-zeroing',
    0x09: "Reserved (0x9)",
    0x0A: "Reserved (0xA)",
    0x0B: "Reserved (0xB)",
    0x0C: "Reserved (0xC)",
    0x0D: "Reserved (0xD)",
    0x0E: "Reserved (0xE)",
    0x0F: "Reserved (0xF)",
    0x10: 'Zero Scale',
    0x11: 'Enforced Zero Return'
}

class AttributeReport(object):
    def __init__(self, report_data=[]):
        assert len(report_data == 3)
        _, scale_class, units = tuple(report_data)

        self._scale_class = SCALE_CLASSES[scale_class]
        self._units = WEIGHT_UNITS[units]

    @property
    def scale_class(self):
        return self._scale_class


class ControlReport(object):
    def __init__(self, report_data=[]):
        assert len(report_data == 2)

        _, control_data = tuple(report_data)

        self._enforced_zero_return = (control_data & 0x1)
        self._zero_scale = (control_data & 0x2)

    @property
    def ezr_enabled(self):
        return bool(self._enforced_zero_return)

    @property
    def zs_enabled(self):
        return bool(self._zero_scale)


class DataReport(object):
    def __init__(self, report_data=[]):
        assert len(report_data) == 6

        _, status, units, scaling, weight_lsb, weight_msb = tuple(report_data)

        self._status = SCALE_STATUSES[status]
        self._units = WEIGHT_UNITS[units]
        self._scaling = (~scaling & 0xFF) - 1 if (scaling & 0x80) else scaling
        self._weight = (weight_msb << 8 | weight_lsb) * pow(10, self._scaling)

    def __str__(self):
        return '[%s] %s %s' % (self.status, self.weight, self.units)

    @property
    def stable(self):
        return self._status == 'Weight Stable'

    @property
    def status(self):
        return self._status

    @property
    def units(self):
        return self._units

    @property
    def weight(self):
        return round(self._weight, 1) if self.units == 'oz' else self._weight


class StatusReport(object):
    def __init__(self, report_data=[]):
        assert len(report_data) == 2

        _, status = tuple(report_data)
        self.status = SCALE_STATUSES[status]

    @property
    def status(self):
        return self.status


class WeightLimitReport(object):
    def __init__(self, report_data=[]):
        assert len(report_data) == 5

        _, units, scaling, weight_lsb, weight_msb = tuple(report_data)

        self._units = WEIGHT_UNITS[units]
        self._scaling = (~scaling & 0xFF) - 1 if (scaling & 0x80) else scaling
        self._weight = (weight_msb << 8 | weight_lsb) * pow(10, self._scaling)

    @property
    def units(self):
        return self._units

    @property
    def weight(self):
        return round(self._weight, 1) if self.units == 'oz' else self._weight


class StatisticsReport(object):
    def __init__(self, report_data=[]):
        assert len(report_data) == 5
        (
            _,
            calibration_lsb,
            calibration_msb,
            rezero_lsb,
            rezero_msb
        ) = tuple(report_data)

        self._calibration_count = (calibration_msb << 8 | calibration_lsb)
        self._rezero_count = (rezero_msb << 8 | rezero_lsb)

    @property
    def calibration_count(self):
        return self._calibration_count

    @property
    def rezero_count(self):
        return self._rezero_count


REPORT_TYPES = {
    0x1: AttributeReport,
    0x2: ControlReport,
    0x3: DataReport,
    0x4: StatusReport,
    0x5: WeightLimitReport,
    0x6: StatisticsReport
}

connected_devices = [
    (device_info.get('vendor_id'), device_info.get('product_id'))
    for device_info in hid.enumerate()
]

connected_scales = [
    device for device in connected_devices if device in SUPPORTED_DEVICES
]

scales = []
for vendor_id, product_id in connected_scales:
   try:
       device = hid.device()
       device.open(vendor_id, product_id) # idVendor idProduct
   except IOError as e:
       print(e)
   else:
       scales.append(device)

if not scales:
    print('No scales are connected!')

for scale in scales:

    print('Manufacturer: %s' % scale.get_manufacturer_string())
    print('Product: %s' % scale.get_product_string())
    print('Serial No: %s' % scale.get_serial_number_string())

    # try non-blocking mode by uncommenting the next line
    #scale.set_nonblocking(1)

    # try writing some data to the device
    for k in range(10):
        for i in [0, 1]:
            for j in [0, 1]:
                res = scale.write([0x80, i, j])
                report_data = scale.read(6)
                if report_data:
                    report = REPORT_TYPES[report_data[0]](report_data)
                    print(report)

                time.sleep(0.05)

    print('Closing device')
    scale.close()

print('Done')
# =======
# from importlib import import_module
#
# for module_name in ('device_libusb1', 'device_pyusb1', 'device_pyusb',
#                     'device_ctypes_hidapi', 'device_cython_hidapi'):
#     try:
#         print(module_name)
#         module = import_module('silverscale.' + module_name)
#         USBDevice = getattr(module, 'USBDevice')
#         break
#     except ImportError as error:
#         print(error)
# else:
#     raise ImportError('No USB library found')
#
# scale = USBDevice(0x922, 0x8004)
#
# >>>>>>> 4b9ee7e9acc514437e3047fd5a66b04d09da085a
