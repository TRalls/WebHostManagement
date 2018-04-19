#!/usr/bin/env python3
"""
    Interfaces with the OS to pull system health metrics as part of Web Host Manager.
    The output of this program is a dictionary of system health data points.
    This file records steps in whm.log

    Dependancies:
        python3.5 or higher
        lm-sensors
"""

import subprocess
import os
import sys
import random
from logger import Logger

# decare local globals
report = {}
logger = Logger("TempUser", "metrics.py")
path = os.path.abspath(os.path.dirname(__file__))
globe = {
    "demo" : False,
    "full_report" : True
}

def main():

    logger.write('Began collecting metrics: ' + ' '.join(sys.argv[:]))

    # check params and ensure proper usage
    if len(sys.argv) == 2 and sys.argv[1] == "update":
        globe["full_report"] = False
        logger.write('Collecting temperature metrics only.')
    elif len(sys.argv) != 1:
        print("Use no argument for a full report or use 'update' for only a tempurature report.")
        logger.write('Unexprected parameters - Did not collect metrics.')
        exit(1)

    # attempt to pull sensor data
    (sensorsOut, sensorsRC) = toOS("sensors -u")
    if sensorsOut == "failed":
        logger.write("No metrics collected")
        exit(2)

    # if sensors executed but returned an error
    # this signifies 'demo' mode should be used and fake metrics will be used to demonstrate program functionality
    if sensorsRC == 1:
        globe["demo"] = True
        (sensorsOut, sensorsRC) = toOS("cat " + os.path.join(path, "samples/sample-sensors.txt"))
        logger.write('Demo Mode: Demo metrics pulled from sample-sensors.txt.')

    # extract individual device data
    report["sensors"] = {}
    devices = []
    deviceOut = ""
    sensorsOutI = 0
    sensorsOutLen = len(sensorsOut)
    for c in sensorsOut:
        deviceOut += c
        if sensorsOutI > 1:
            if ((ord(c) == 10 and ord(sensorsOut[sensorsOutI - 1]) == 10) or sensorsOutI == sensorsOutLen - 1):
                devices.append(deviceOut)
                deviceOut = ""
                deviceOutLen = 0
        sensorsOutI += 1

    # extract info out from device data
    devicen = 0
    for device in devices:
        # prepare report to recieve device names
        report["sensors"]["device" + str(devicen)] = {
            "name0" : "",
            "name1" : ""
        }
        i = 0

        # pull out name0
        while ord(device[i]) != 10:
            report["sensors"]["device" + str(devicen)]["name0"] += device[i]
            i += 1

        # skip "Adapter: "
        while device[i] != " ":
            i += 1
        i += 1

        # pull out name1
        while ord(device[i]) != 10:
            report["sensors"]["device" + str(devicen)]["name1"] += device[i]
            i += 1

        # pull out values
        values = {}
        deviceLen = len(device)
        while i < deviceLen:                    # iterate device to the end of its output
            key, value = "", ""
            while ord(device[i]) != 10:         # iterates to end of line
                while device[i] != ":":         # ":" signifies a potential end of key
                    if device[i] != " ":
                        key += device[i]        # build key
                    i += 1
                while ord(device[i]) != 10:     # iterate to end of line while building a value
                    if device[i] != " " and device[i] != ":":
                        value += device[i]
                    i += 1
            if len(value) > 0:
                values[key] = value             # if a value was built before end of line, the pair is saved
            i += 1

        # values are stored in report
        report["sensors"]["device" + str(devicen)]["values"] = values
        devicen += 1

    logger.write('Sensors parsed and added to report.')

    # exit if full report was not requested
    if not globe["full_report"]:
        logger.write('Reported sensors only.')
        exit(0)

    # pull and report uptime (works on virts)
    (report['uptime'], uptimeRC) = toOS("uptime -p | cut -c 4- | tr -d '\n'")


    # fruther metrics gathering


    logger.write(str(report))
    logger.write('Full report generated.')


def toOS(command):
    # attempt to send command to OS
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out = result.stdout.decode('utf-8')
        rc = result.returncode
        if rc == 0:
            logger.write('Successfully ran ' + command + '.')
        else:
            logger.write('OS took command, but there was an issue: ' + command + '.')
        return (out, rc)
    except:
        print('Host failed to handle ' + command)
        logger.write('Host failed to handle ' + command)
        return ("failed", -1)

if __name__ == "__main__":
    main()