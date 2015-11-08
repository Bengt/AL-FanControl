"""Python side of the Python to Arduino bridge."""

from __future__ import print_function

from multiprocessing import Process, Queue

import serial

from temperatures import get_temps
from util import (
    clip_pwm, format_buffers, format_decisions, format_differences,
    format_directions, format_fans, format_hysteresises, format_limits,
    format_names, format_ports, format_pwms, format_pwms_new, format_rpms,
    format_temps, format_tmps, message_to_rpms, pwms_to_message, signum)

SCALING_FACTOR = 0.05  # usually in (0.01, 0.1)


def _reader(console, queue_read):
    while True:
        try:
            response = console.readline().decode('ASCII')
        except TypeError:
            pass
        response = response.strip()
        if response != '':
            queue_read.put(response)


def _writer(console, queue_write):
    while True:
        try:
            message = queue_write.get()
        except KeyboardInterrupt:
            break
        console.writelines([message.encode('ASCII')])


def main():
    pwms = [178, 255, 255, None, 45, None, None, None]  # at idle
    ports = [0, 1, 2, 3, 4, 5, 6, 7, ]
    fans = ['CPU', 'Case', 'Case', None, 'GPU', None, None, None]
    chips = ['k10temp', 'it8718', 'it8718', None, 'radeon', None, None, None]
    features = ['temp1', 'temp1', 'temp1', None, 'temp1', None, None, None]
    limits = [55, 40, 50, None, 75, None, None, None]
    hysteresises = [3, 3, 3, None, 3, None, None, None]

    console = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    queue_read = Queue(maxsize=1)
    queue_write = Queue(maxsize=1)

    reader_t = Process(target=_reader, args=([console, queue_read]))
    reader_t.start()
    writer_t = Process(target=_writer, args=([console, queue_write]))
    writer_t.start()

    while True:
        queue_write.put(pwms_to_message(pwms=pwms))

        try:
            message = queue_read.get()
        except KeyboardInterrupt:
            break
        rpms = message_to_rpms(message=message)

        temps = [
            int(round(temp, 0)) if temp is not None else None
            for temp in get_temps(chips=chips,
                                  features=features)
        ]

        decisions = [
            abs(limit - temp) > hysteresis
            if None not in [limit, temp, hysteresis] else None
            for (limit, temp, hysteresis) in zip(limits, temps, hysteresises)
        ]

        directions = [
            signum(limit - temp) if None not in [limit, temp] else None
            for (limit, temp) in zip(limits, temps)
        ]

        differences = [
            int(round(pwm * direction * SCALING_FACTOR, 0))
            if decision else None
            for (pwm, direction, decision) in zip(pwms, directions, decisions)
        ]

        pwms_new = [
            clip_pwm(int(round(pwm + difference, 0)))
            if None not in [pwm, difference] else pwm
            for (pwm, difference) in zip(pwms, differences)
        ]

        print(format_fans(fans=fans))
        print(format_ports(ports=ports))
        print(format_pwms(pwms=pwms))
        print(format_rpms(rpms=rpms))
        print(format_temps(temps=temps))
        print(format_limits(limits=limits))
        print(format_hysteresises(hysteresises=hysteresises))
        print(format_decisions(decisions=decisions))
        print(format_directions(directions=directions))
        print(format_differences(differences=differences))
        print(format_pwms_new(pwms_new=pwms_new))
        print()

        pwms = pwms_new

    reader_t.terminate()
    writer_t.terminate()


if __name__ == '__main__':
    main()
