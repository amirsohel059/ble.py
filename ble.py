import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib
from pydbus import SystemBus
import os
import subprocess

SERVICE_NAME = 'org.bluez'
ADAPTER_IFACE = 'org.bluez.Adapter1'
DEVICE_IFACE = 'org.bluez.Device1'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
BLUEZ_SERVICE_NAME = 'org.bluez'
BLUEZ_ADAPTER_PATH = '/org/bluez/hci0'
GATT_CHRC_UUID = '0000xxxx-0000-1000-8000-00805f9b34fb'
GATT_SERVICE_UUID = '0000xxxx-0000-1000-8000-00805f9b34fb'

class WiFiProvisioningService(dbus.service.Object):
    def __init__(self, bus, index):
        self.path = f'/org/bluez/example/service{index}'
        self.bus = bus
        self.uuid = GATT_SERVICE_UUID
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_characteristic(WiFiProvisioningCharacteristic(bus, 0, self))

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': True,
                'Characteristics': dbus.Array(self.get_characteristic_paths(), signature='o')
            }
        }

    def get_characteristic_paths(self):
        result = []
        for characteristic in self.characteristics:
            result.append(characteristic.get_path())
        return result

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise dbus.exceptions.DBusException(
                'org.freedesktop.DBus.Error.InvalidArgs')
        return self.get_properties()

    def add_characteristic(self, characteristic):
        self.characteristics.append(characteristic)

class WiFiProvisioningCharacteristic(dbus.service.Object):
    def __init__(self, bus, index, service):
        self.path = f'{service.path}/char{index}'
        self.bus = bus
        self.uuid = GATT_CHRC_UUID
        self.service = service
        self.flags = ['read', 'write']
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'UUID': self.uuid,
                'Service': self.service.get_path(),
                'Flags': self.flags
            }
        }

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise dbus.exceptions.DBusException(
                'org.freedesktop.DBus.Error.InvalidArgs')
        return self.get_properties()

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='ay', out_signature='ay')
    def ReadValue(self, options):
        print("ReadValue called")
        return []

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='ayay', out_signature='')
    def WriteValue(self, value, options):
        print("WriteValue called")
        credentials = bytes(value).decode('utf-8')
        ssid, password = credentials.split(',')
        self.connect_to_wifi(ssid, password)

    def connect_to_wifi(self, ssid, password):
        try:
            with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'a') as wpa_file:
                wpa_file.write(f'\nnetwork={{\n\tssid="{ssid}"\n\tpsk="{password}"\n}}')
            
            subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'], check=True)
            print(f"Connected to WiFi network: {ssid}")
        except Exception as e:
            print(f"Failed to connect to WiFi: {e}")

def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = SystemBus()

    adapter = bus.get(SERVICE_NAME, BLUEZ_ADAPTER_PATH)
    adapter_props = dbus.Interface(adapter, dbus.PROPERTIES_IFACE)
    
    try:
        adapter_props.Set(ADAPTER_IFACE, 'Powered', dbus.Boolean(1))
    except dbus.exceptions.DBusException as e:
        print(f"Failed to set adapter powered on: {e}")

    service = WiFiProvisioningService(bus, 0)
    manager = dbus.Interface(bus.get_object(SERVICE_NAME, BLUEZ_ADAPTER_PATH), GATT_MANAGER_IFACE)
    try:
        manager.RegisterApplication(service.get_path(), {},
                                    reply_handler=lambda: print('GATT application registered'),
                                    error_handler=lambda e: print(f'Failed to register application: {e}'))
    except dbus.exceptions.DBusException as e:
        print(f"Failed to register GATT application: {e}")

    mainloop = GLib.MainLoop()
    mainloop.run()

if __name__ == '__main__':
    main()
