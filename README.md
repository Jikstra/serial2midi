# Serial2MIDI

This CLI tool allows you to "convert" your serial device to virtual midi device. It also supports sending midi back to the serial device.
You can use this tool with ALSA & Jack.


# Install

## Arch

There is a PKGBUILD in the [AUR](https://aur.archlinux.org/packages/serial2midi-git/). Download it and install it like any other PKGBUILD or use an AUR helper like yay.

`yay -S serial2midi-git`

## From git

1. Clone this repository `git clone https://github.com/jikstra/serial2midi.git`
2. cd into the folder `cd serial2midi`
3. install python dependencies with `pip install -r dependencies.txt`
4. run the tool with `python main.py`
5. Copy it to your path, for example `cp main.py /usr/bin/serial2midi`
6. No you can run it just by running `serial2midi`

# Usage
```
usage: serial2midi [-h] [--name NAME] [--baud-rate BAUD_RATE] [--sleep-interval SLEEP_INTERVAL] DEVICE

Convert a USB Serial device to a Midi device

positional arguments:
  DEVICE                Path to the serial device

optional arguments:
  -h, --help            show this help message and exit
  --name NAME           Name of the virtual midi device (default: Serial2MIDI)
  --baud-rate BAUD_RATE
                        Baud rate of serial device (default: 115200)
  --sleep-interval SLEEP_INTERVAL
                        How many seconds we wait between looking for reconnected device. Float is possible. (default: 0.3)
```



