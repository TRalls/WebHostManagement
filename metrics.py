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
    (report['uptime'], _) = toOS("uptime -p | cut -c 4- | tr -d '\n'")
    logger.write("Added uptime to report.")

    # pull and report dmesg (virts us sample output)
    if not globe["demo"]:
        (report['dmesg'], _) = toOS("dmesg | tail -n 200")
        logger.write("Added dmesg to report.")
    else:
        (report['dmesg'], _) = toOS("cat " + os.path.join(path, "samples/sample-dmesg.txt"))
        logger.write("Demo Mode: Demo metrics pulled from sample-dmesg.txt.")

    # pull and report memory stats (works on virts)
    (freeOut, _) = toOS("free -o")
    i = 0
    freeOutLen = len(freeOut)

    # skip first line of output
    while ord(freeOut[i]) != 10:
        i += 1
    i += 1

    # scan over freeOut and identify data point to save in report
    report["Memory"] = {}
    while i < freeOutLen:
        # get name
        name = ""
        while freeOut[i] != ":":
            name += freeOut[i]
            i += 1
        i += 1

        # get total
        total = ""
        while freeOut[i] == " ":
            i += 1
        while freeOut[i] != " ":
            total += freeOut[i]
            i += 1

        # get used
        used = ""
        while freeOut[i] == " ":
            i += 1
        while freeOut[i] != " ":
            used += freeOut[i]
            i += 1

        # save data
        report["Memory"][name] = {
            "total": total,
            "used": used
        }

        # burn through rest of line
        while ord(freeOut[i]) != 10:
            i += 1
        i += 1

    logger.write('Memory stats collected.')

    # pull and report storage status (demo mode uses sample output)
    if not globe["demo"]:
        (lsblkOut, _) = toOS("lsblk | tail -n +2")
        logger.write("Pulling pysical drive info.")
    else:
        (lsblkOut, _) = toOS("cat " + os.path.join(path, "samples/sample-lsblk.txt"))
        logger.write("Demo Mode: Demo metrics pulled from sample-lsblk.txt.")

    # extract data from output
    i = 0                   # i is index in output
    heritage = []
    lsblkOutLen = len(lsblkOut)
    report["drives"] = {}
    while i < lsblkOutLen:
        j = 0               # j tracks the nexted position of device name
        while ord(lsblkOut[i]) != 10:
            while not (97 <= ord(lsblkOut[i]) <= 122 or 48 <= ord(lsblkOut[i]) <= 57):
                i += 1
                j += .5
            name = ""
            while 97 <= ord(lsblkOut[i]) <= 122 or 48 <= ord(lsblkOut[i]) <= 57:
                name += lsblkOut[i]
                i += 1
            for x in range(2):
                while lsblkOut[i] == " ":
                    i += 1
                while lsblkOut[i] != " ":
                    i += 1
            while lsblkOut[i] == " ":
                i += 1
            size = ""
            while lsblkOut[i] != " ":
                size += lsblkOut[i]
                i += 1
            while lsblkOut[i] == " ":
                i += 1
            while lsblkOut[i] != " ":
                i += 1
            while lsblkOut[i] == " ":
                i += 1
            dtype = ""
            while not ord(lsblkOut[i]) in [10, 32]:
                dtype += lsblkOut[i]
                i += 1
            while lsblkOut[i] == " " and ord(lsblkOut[i]) != 10:
                i += 1
            mount = ""
            while ord(lsblkOut[i]) != 10:
                mount += lsblkOut[i]
                i += 1

            if j == 0:
                # root element
                heritage = [[name, j]]
            elif j == heritage[len(heritage) - 1][1] + 1:
                # child of last element
                heritage.append([name, j])
            elif j < heritage[len(heritage) - 1][1]:
                # this is an aunt, but not a root
                heritage = heritage[:j - 1]
            else:
                # sibling
                heritage.pop().append([name, j])

            # add info to report
            if j == 0:
                report["drives"][name] = {
                    "size": size,
                    "type": dtype
                }
                if len(mount) > 0:
                    report["drives"][name]["mount"] = mount
            if j > 0:
                parent = report["drives"]
                herLen = len(heritage)
                for device in heritage:
                    if device[0] != heritage[herLen - 1][0]:
                        parent = parent[device[0]]
                if not "children" in parent:
                    parent["children"] = {}
                parent["children"][name] = {
                    "size": size,
                    "type": dtype
                }

            print(name + ", " + str(j) + ", " + size + ", " + dtype + ", " + mount + " - heritage: " + str(heritage))
            print(report["drives"])
        i += 1

    # fruther metrics gathering

    print(report["drives"])
    logger.write('Full report generated.')

    #logger.write(str(report))


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