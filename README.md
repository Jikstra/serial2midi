# WARNING: Development continued here: https://codeberg.org/obsoleszenz/serial2midi

# Serial2MIDI

This CLI tool allows you to "convert" your serial device to virtual midi device. It also supports sending midi back to the serial device.
You can use this tool with ALSA & Jack. This tool is handy with microcontrollers like arduino uno/mega which don't support USB Midi.


## Features

- Supports ALSA & Jack as audio backends
- You can set name & baud rate
- Full duplex, this means you can not only receive midi but also send midi back to the serial device
- Auto reconnect, if you disconnect the serial device, the virtual midi device is still there and continues working if you plug the serial device in again 
- use python expression to match your device
- supports midi sysex identity, usb pid/vid...


## Examples

Convert `/dev/ttyUSB0` to a midi device
```
serial2midi --match "device_info.device_path == '/dev/ttyUSB0'"
```

List all connected usb serial devices and it's properties
```
serial2midi --list
```

Filter the list of all connected usb serials for the ones that contain "USB2.0" in the description string
```
serial2midi --list --match "device_info.usb_description.find('USB2.0') != -1"
```

Convert usb serial device with usb product id 29987 to a virtual midi device with the name "MidiFoo"
```
serial2midi --name "MidiFoo" --match "device_info.usb_pid == 29987"
```

Set the baudrate
```
serial2midi --baud-rate 96000 --name "MidiFoo" --match "device_info.usb_pid == 29987"
```

# Install

## Arch

There is a PKGBUILD in the [AUR](https://aur.archlinux.org/packages/serial2midi-git/). Download it and install it like any other PKGBUILD or use an AUR helper like yay.

`yay -S serial2midi-git`

## From git/source

1. Clone this repository `git clone https://github.com/jikstra/serial2midi.git`
2. cd into the folder `cd serial2midi`
3. install python dependencies with `pip install -r dependencies.txt`
4. run the tool with `python main.py`
5. Optionally, copy it to a folder in your path, for example `cp main.py /usr/bin/serial2midi`

# Usage
```
usage: serial2midi [-h] [--name NAME] [--baud-rate BAUD_RATE]
                   [--sleep-interval SLEEP_INTERVAL] [--match EVAL_MATCH]
                   [--list]

Convert a USB Serial device to a Midi device

options:
  -h, --help            show this help message and exit
  --name NAME           Name of the virtual midi device (default:
                        Serial2MIDI)
  --baud-rate BAUD_RATE
                        Baud rate of serial device (default: 115200)
  --sleep-interval SLEEP_INTERVAL
                        How many seconds we wait between looking for
                        reconnected device. Float is possible. (default:
                        0.3)
  --match EVAL_MATCH    Use a python expression to find matching devices.
                        See --list for a list of available properties.
                        Example:
                        --match="device_info.midi_identity.manufacturer ==
                        '0x6f'" (default: None)
  --list                List available devices (default: False)
```


# Hacking

## Logging

Currently you can change the log level by manually adjusting the `LOG_LEVELS` array. 
