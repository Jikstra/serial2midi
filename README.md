# Serial2MIDI

This CLI tool allows you to "convert" your serial device to virtual midi device. It also supports sending midi back to the serial device.
You can use this tool with ALSA & Jack.


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



