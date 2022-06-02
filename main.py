#!/usr/bin/python

import rtmidi
import serial
import serial.tools.list_ports
import time
import traceback
import sys
import threading
from enum import Enum
import asyncio

MIDI_SYSEX = 0xF0
MIDI_SYSEX_TYPE_NON_REALTIME = 0x7E
MIDI_SYSEX_END = 0xF7
MIDI_SYSEX_GENERAL_INFORMATION = 0x06
MIDI_SYSEX_REQUEST_IDENTITY = 0x01
MIDI_SYSEX_REPLY_IDENTITY = 0x02

class LogLevel(Enum):
    INFO = 1,
    WARN = 2,
    ERROR = 3,
    DEBUG = 4,
    VERBOSE = 5

#LOG_LEVELS = [LogLevel.INFO, LogLevel.WARN, LogLevel.ERROR, LogLevel.DEBUG]
LOG_LEVELS = [LogLevel.INFO]

def logger(level: LogLevel):
    if level not in LOG_LEVELS:
        return lambda * args: None
    return lambda *args: print("[" + level.name + "]", *args)

error = logger(LogLevel.ERROR)
warn = logger(LogLevel.WARN)
debug = logger(LogLevel.DEBUG)
info = logger(LogLevel.INFO)
verbose = logger(LogLevel.VERBOSE)

# Small helper, see https://stackoverflow.com/questions/2352181/how-to-use-a-dot-to-access-members-of-dictionary
class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

class MidiError(Exception):
    pass

def find_device_port_by_serial_attribute(serial_attribute):
    #context = pyudev.Context()
    #for device in context.list_devices().match_attribute("serial", "0000:00:1a.0"):
    #    return device.device_node
    #return ""
    for p in serial.tools.list_ports.comports():
        device_path = p.device
        context = pyudev.Context()
        device = pyudev.Devices.from_device_file(filename=device_path, context=context)
        for a in device.ancestors:
            try:
                _serial = a.attributes.get('serial').decode('utf-8')
                print(_serial)
                if _serial == serial_attribute:
                    return device_path
            except:
                pass

    return ""



def logException(e):
    error("ERROR", e)
    print(traceback.format_exc())
    print(sys.exc_info()[0])


def serial_set_callback(serial, cb, on_exception):
    interrupt_event = threading.Event()
    def worker():
        try:
            while not interrupt_event.is_set():
                buf = serial.read(3)
                cb(buf)
        except Exception as e:
            on_exception(e)
        verbose("Stopped worker")
        
    thread = threading.Thread(target=worker)
    thread.start()

    def stop():
        interrupt_event.set()
        thread.join()
                
    return stop

class Serial2Midi():
    def __init__(self, name, baud_rate, sleep_interval, eval_match):
        self.name = name
        self.sleep_interval = sleep_interval
        self.baud_rate = baud_rate
        self.start_time = time.time()
        self.eval_match = eval_match

        self.should_stop = False
        self._trigger_interrupt = None
        

    async def run(self):
        virtualMidiInput = rtmidi.MidiIn()
        virtualMidiInput.set_client_name(self.name)
        virtualMidiInput.open_virtual_port(self.name)
        virtualMidiOutput = rtmidi.MidiOut()
        virtualMidiOutput.set_client_name(self.name)
        virtualMidiOutput.open_virtual_port(self.name)

        found_device = True
        device_path = ""
        last_iteration_could_not_find_device = False
        while self.should_stop is False:
            devices = [d async for d in findDevices(self.eval_match)]
            if len(devices) > 1:
                info("Found more then one device matching, taking the first one ({})".format(devices[0].device_path))
            elif len(devices) == 0:
                if last_iteration_could_not_find_device is not True:
                    info("Could not find device. Is it connected?")
                    last_iteration_could_not_find_device = True

                time.sleep(self.sleep_interval)
                continue
            
            last_iteration_could_not_find_device = False
            device_path = devices[0].device_path

            info("Device path: " + device_path)
            try:
                serialMidi = None
                try:
                    serialMidi = serial.Serial(device_path, self.baud_rate, timeout=1, exclusive=True)
                except serial.SerialException as e:
                    if found_device == True:
                        info("Could not connect to ", device_path, ". Error: " + str(e))
                        found_device = False
                    time.sleep(self.sleep_interval)
                    continue
                except Exception as e:
                    logException(e)
                    serialMidi.close()

                info("Opened device \"{}\" as \"{}\" with baud rate of {}".format(device_path, self.name, self.baud_rate))
                found_device = True

                interrupt = threading.Event()
                self._trigger_interrupt = lambda: interrupt.set()

                virtualMidiInput.set_callback(lambda midi_message, time: self.process_serial_output(midi_message[0], serialMidi))

                def on_serial_exception(exception):
                    logException(exception)
                    self._trigger_interrupt()
                stop_serial = serial_set_callback(serialMidi, lambda buf: self.process_serial_input(buf, virtualMidiOutput), on_serial_exception)

                interrupt.wait()
                
                verbose("Interrupted main loop")
                
                stop_serial()
                serialMidi.close()
            except Exception as e:
                logException(e)

            time.sleep(self.sleep_interval)
        
        virtualMidiInput.close_port()
        virtualMidiOutput.close_port()
        verbose("Main loop exit")
    
    def trigger_interrupt(self):
        if self._trigger_interrupt is not None:
            verbose("Triggering interrupt")
            self._trigger_interrupt()
    
    def stop(self):
        if self.should_stop is True:
            return
        print("\n")
        info("Stopping...")
        self.should_stop = True
        self.trigger_interrupt()
    
    def process_serial_input(self, buf, virtualMidiOutput):
        len_buf = len(buf)
        if len_buf == 3:
            split = [buf[i] for i in range (0, len(buf))]
            info(self.time_since_start(), "[MIDI <-]", hex(split[0]), hex(split[1]), hex(split[2]))
            virtualMidiOutput.send_message(buf)
        elif len_buf > 0:
            warn("Buffer incomplete")

    def process_serial_output(self, buf, serialMidi):
        try:
            if buf is not None:
                info(self.time_since_start(), "[MIDI ->]", hex(buf[0]), hex(buf[1]), hex(buf[2]))
                serialMidi.write(buf)
        except Exception as e:
            logException(e)
            self.trigger_interrupt()

    def time_since_start(self):
        return time.time() - self.start_time

def deviceIsExclusive(device, timeout=4):
    try:
        serial.Serial(device, 115200, timeout=3, exclusive=True)
    except serial.serialutil.SerialException:
        return False
    return True

def sysexIdentityRequest(device, timeout=4):
    try:
        serialMidi = serial.Serial(device, 115200, timeout=3, exclusive=True)
    except serial.serialutil.SerialException:
        return False

    def readOneByte():
        return int.from_bytes(serialMidi.read(), 'little', signed=False)

    def cleanBufferFromSysEx():
        while readOneByte() != MIDI_SYSEX_END:
            pass

    def tryParsingSysexIdentityReply():
        sysex_byte = readOneByte()
        if sysex_byte != MIDI_SYSEX:
            debug('Received 0x{:02X}, but waiting for MIDI_SYSEX (0x{:02X})...'.format(sysex_byte, MIDI_SYSEX))
            return False

        debug('received sysex message...')

        sysex_nonrealtime_type = readOneByte()
        if sysex_nonrealtime_type != MIDI_SYSEX_TYPE_NON_REALTIME:
            debug('Received sysex type of 0x{:02X}, but expected MIDI_SYSEX_TYPE_NON_REALTIME (0x{:02X}). Aborting.'.format(sysex_nonrealtime_type, MIDI_SYSEX_TYPE_NON_REALTIME))
            return False

        sysex_channel = readOneByte()
        debug('sysex channel is 0x{:02X}'.format(sysex_channel))

        sysex_general_information = readOneByte()
        if sysex_general_information != MIDI_SYSEX_GENERAL_INFORMATION:
            raise MidiError('[err] Received sysex action of 0x{:02X}, but expected MIDI_SYSEX_GENERAL_INFORMATION (0x{:02X}) Aborting.'.format(sysex_general_information, MIDI_SYSEX_GENERAL_INFORMATION))

        sysex_reply_identity = readOneByte()
        if sysex_reply_identity != MIDI_SYSEX_REPLY_IDENTITY:
            raise MidiError('Received sysex reply of 0x{:02X}, but expected MIDI_SYSEX_REPLY_IDENTITY (0x{:02X})'.format(sysex_reply_identity, MIDI_SYSEX_REPLY_IDENTITY))

        manufacturer_id = readOneByte()
        family_code_one = readOneByte()
        family_code_two = readOneByte()
        model_number_one = readOneByte()
        model_number_two = readOneByte()
        version_number_one = readOneByte()
        version_number_two = readOneByte()
        version_number_three = readOneByte()
        version_number_four = readOneByte()

        identity = {
            "manufacturer": "0x{:02x}".format(manufacturer_id),
            "family_code": "{}.{}".format(family_code_one, family_code_two),
            "model_number": "{}.{}".format(model_number_one, model_number_two),
            "version": "{}.{}.{}.{}".format(version_number_one, version_number_two, version_number_three, version_number_four)
        }

        sysex_end = readOneByte()
        if sysex_end != MIDI_SYSEX_END:
            raise MidiError('Received byte of 0x{:02X}, but expected MIDI_SYSEX_END (0x{:02X}) Aborting.'.format(sysex_end, MIDI_SYSEX_END))

        return identity

    # We need to wait until the arduino is ready to read...
    start = time.time()

    while time.time() - start < 3.0:
        if serialMidi.in_waiting > 0:
            identity = tryParsingSysexIdentityReply()
            if identity is not False:
                return identity



    serialMidi.write(bytearray([
        MIDI_SYSEX,
        MIDI_SYSEX_TYPE_NON_REALTIME,
        0x1,
        MIDI_SYSEX_GENERAL_INFORMATION, 
        MIDI_SYSEX_REQUEST_IDENTITY,
        MIDI_SYSEX_END
    ]))
    serialMidi.flush()
    debug("Sent request")

    while time.time() - start < timeout:
        identity = tryParsingSysexIdentityReply()
        if identity is not False:
            return identity
    return False

async def findDevices(eval_match):
    import serial.tools.list_ports

    async def task(port_info):

        device_info = dotdict({
            'device_path': port_info.device,
            'usb_description': port_info.product,
            'usb_vid': port_info.vid,
            'usb_pid': port_info.pid,
            'usb_location': port_info.location,
            'usb_manufacturer': port_info.manufacturer,
            'exclusive': deviceIsExclusive(port_info.device),
            'midi_identity': dotdict({
                'manufacturer': None,
                'family_code': None,
                'model_number': None,
                'version': None
            })

        })
        #identity = sysexIdentityRequest(port_info.device)
        
        identity = False

        try:
            identity = await asyncio.to_thread(sysexIdentityRequest, port_info.device)
        except Exception as e:
            print("\nError in sysexIdentityRequest():\n {}".format(traceback.format_exc()))

        if identity is not False:
            device_info.midi_identity = dotdict({
                'manufacturer': identity['manufacturer'],
                'family_code': identity['family_code'],
                'model_number': identity['model_number'],
                'version': identity['version']
            })
        return device_info

    ports = serial.tools.list_ports.comports()
    for device_info_task in asyncio.as_completed([task(port_info) for port_info in ports]):
        device_info = await device_info_task
        should_yield = True

        if eval_match is not None:
            try: 
                should_yield = eval(eval_match)
            except Exception as e:
                print("\nError in match-eval:\n {}".format(traceback.format_exc()))
                should_yield = False


        if should_yield:
            yield device_info


async def listDevices(eval_match):
    if eval_match is not None:
        print("eval match: {}".format(eval_match))
    print("# Devices")
    i = 0

    async for port_info in findDevices(eval_match):
        print(" ")
        for key, value in port_info.items():
            if key == 'midi_identity' and value is not None:
                for sub_key, sub_value in value.items():
                    print("device_info.{}.{}: {}".format(key, sub_key, sub_value))
                continue

            print("device_info.{}: {}".format(key, value))
        i += 1

    if i == 0:
        print("No devices found :/")

async def main():
    import argparse

    parser = argparse.ArgumentParser(prog='serial2midi', description='Convert a USB Serial device to a Midi device', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--name', dest='name', default='Serial2MIDI',
                        help='Name of the virtual midi device')
    parser.add_argument('--baud-rate', dest='baud_rate', default=115200,
                        help='Baud rate of serial device')
    parser.add_argument('--sleep-interval', dest='sleep_interval', default=0.3,
                        help='How many seconds we wait between looking for reconnected device. Float is possible.')
    parser.add_argument('--match', dest='eval_match', default=None, help='Use a python expression to find matching devices. See --list for a list of available properties.\n Example: --match="device_info.midi_identity.manufacturer == \'0x6f\'"')

    parser.add_argument('--list', default=False, action="store_true", help='List available devices')
    args = parser.parse_args()

    if args.list:
        await listDevices(args.eval_match)
        return 0

    serial_to_midi = Serial2Midi(args.name, args.baud_rate, args.sleep_interval, args.eval_match)

    
    import signal
    for sig in ('TERM', 'HUP', 'INT'):
        signal.signal(getattr(signal, 'SIG'+sig), lambda signo, _frame: serial_to_midi.stop());

    await serial_to_midi.run()

if __name__ == '__main__':
    asyncio.run(main())
