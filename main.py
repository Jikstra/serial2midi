#!/usr/bin/python

import rtmidi
import serial
import time
import traceback
import sys
import threading
from enum import Enum

class LogLevel(Enum):
    INFO = 1,
    WARN = 2,
    ERROR = 3,
    DEBUG = 4,
    VERBOSE = 5

LOG_LEVELS = [LogLevel.INFO, LogLevel.WARN, LogLevel.ERROR, LogLevel.DEBUG]

def logger(level: LogLevel):
    if level not in LOG_LEVELS:
        return lambda * args: None
    return lambda *args: print("[" + level.name + "]", *args)

error = logger(LogLevel.ERROR)
warn = logger(LogLevel.WARN)
debug = logger(LogLevel.DEBUG)
info = logger(LogLevel.INFO)
verbose = logger(LogLevel.VERBOSE)

def logException(e):
    error("ERROR", e)
    print(traceback.format_exc())
    print(sys.exc_info()[0])


def serial_set_callback(serial, cb, on_exception):
    interrupt_event = threading.Event()
    def worker():
        try:
            while not interrupt_event.isSet():
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
    def __init__(self, device, name, baud_rate, sleep_interval):
        self.name = name
        self.sleep_interval = sleep_interval
        self.device = device
        self.baud_rate = baud_rate


        self.should_stop = False
        self._trigger_interrupt = None
        

    def run(self):
        virtualMidiInput = rtmidi.MidiIn()
        virtualMidiInput.set_client_name(self.name)
        virtualMidiInput.open_virtual_port(self.name)
        virtualMidiOutput = rtmidi.MidiOut()
        virtualMidiOutput.set_client_name(self.name)
        virtualMidiOutput.open_virtual_port(self.name)

        found_device = True
        while self.should_stop is False:
            try:
                serialMidi = None
                try:
                    serialMidi = serial.Serial(self.device, self.baud_rate, timeout=1, exclusive=True)
                except serial.SerialException as e:
                    if found_device == True:
                        info("Could not find device ", self.device, ". Please connect it")
                        found_device = False
                    time.sleep(self.sleep_interval)
                    continue
                except Exception as e:
                    logException(e)
                    serialMidi.close()

                info("Opened device \"{}\" as \"{}\" with baud rate of {}".format(self.device, self.name, self.baud_rate))
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
            debug("[MIDI <-]", hex(split[0]), hex(split[1]), hex(split[2]))
            virtualMidiOutput.send_message(buf)
        elif len_buf > 0:
            warn("Buffer incomplete")

    def process_serial_output(self, buf, serialMidi):
        try:
            if buf is not None:
                debug("[MIDI ->]", hex(buf[0]), hex(buf[1]), hex(buf[2]))
                serialMidi.write(buf)
        except Exception as e:
            logException(e)
            self.trigger_interrupt()


def main():
    import argparse

    parser = argparse.ArgumentParser(prog='serial2midi', description='Convert a USB Serial device to a Midi device', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('device', metavar='DEVICE', default='/dev/ttyUSB0',
                        help='Path to the serial device')
    parser.add_argument('--name', dest='name', default='Serial2MIDI',
                        help='Name of the virtual midi device')
    parser.add_argument('--baud-rate', dest='baud_rate', default=115200,
                        help='Baud rate of serial device')
    parser.add_argument('--sleep-interval', dest='sleep_interval', default=0.3,
                        help='How many seconds we wait between looking for reconnected device. Float is possible.')

    args = parser.parse_args()
    
    serial_to_midi = Serial2Midi(args.device, args.name, args.baud_rate, args.sleep_interval)
    
    import signal
    for sig in ('TERM', 'HUP', 'INT'):
        signal.signal(getattr(signal, 'SIG'+sig), lambda signo, _frame: serial_to_midi.stop());

    serial_to_midi.run()

if __name__ == '__main__':
    main()