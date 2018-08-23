#!/usr/bin/env python3
"""
    Interfaces with the OS to pull system health metrics as part of Web Host Manager.
    The output of this program is a dictionary of system health data points.
    Can be used from the CLI or from other files.

    Dependancies:
        python3.5 or higher
        lm-sensors
        smartmontools
"""

import subprocess
import os
import sys
from logger import Logger

# Decare local globals.
report = {}
path = os.path.abspath(os.path.dirname(__file__))
globe = {
    "demo" : False,
    "full_report" : True,
    "command_line" : False
}

"""
    Target function regardless of running from CLI or other file.
    This functioon will default to providing a full report for a CLI-User unless specified otherwise.
"""
def main(full_report=True, user="CLI-User"):

    # Ensure clear report.
    report.clear()

    # Initialize logger.
    global logger
    logger = Logger(user, "metrics.py")
    logger.write('Began collecting metrics: ' + ' '.join(sys.argv[:]) + ' --------------')

    # Ensure pythong version requirement.
    if sys.version_info < (3,5):
        logger.write('Minimum required python version: 3.5')
        logger.write('Python version detected: ' + str(sys.version_info[0]) + '.' + str(sys.version_info[1]))
        print('Minimum python requirement is not met. See whm.log.')
        exit(1)

    # Detect if ran from command line, and remember.
    if "metrics.py" in sys.argv[0]:
        globe["command_line"] = True
        # If ran from command line, check params and ensure proper usage.
        if len(sys.argv) == 2 and sys.argv[1] == "update":
            globe["full_report"] = False
            logger.write('Running partial report.')
        elif len(sys.argv) != 1:
            print("Use no argument for a full report or use 'update' for a partial report.")
            logger.write('Unexprected parameters - Did not collect metrics.')
            exit(2)

    # Remember if a partial report was requested. This is not applicable to CLI usage.
    if not globe["command_line"]:
        globe["full_report"] = full_report

    # Check if demo mode should be used.
    if iAmAVirt():
        globe["demo"] = True
        logger.write("Demo Mode - Using sample data.")
        report["demo"] = True
    else:
        report["demo"] = False


    # Load partial report.
    loadSensors()
    loadMemory()
    loadLogicalV()
    loadCpu()

    # Load the rest of the report if needed.
    if globe["full_report"]:
        loadVarious()
        loadDrives()
        loadProcesses()

    # Print, log, and return report where applicable.
    if globe["command_line"]:
        print(report)
    logger.write("Report Generated. Full report: " + str(globe["full_report"]) + " --------------")
    return(report)

"""
    Checks to see what sensors returns with. A return code of 1 indicates that system doesn't see local sensors.
    Returns True if this is on a virt, else returns False.
"""
def iAmAVirt():
    # Attempt to pull sensor data.
    (sensorsOut, sensorsRC) = toOS("sensors -u")
    if sensorsOut == "failed":
        logger.write("Exiting - iAmAVirt()")
        exit(3)

    # A return code of 1 indicates sensors do not apply here and this is likely a virtual environment.
    if sensorsRC == 1:
        return True
    else:
        return False

"""
    Load and report sensor data. Temperature and power stats.
"""
def loadSensors():
    # Load sensor info (virts use sample output).
    if not globe["demo"]:
        (sensorsOut, rc) = toOS("sensors -u")
    else:
        (sensorsOut, rc) = toOS("cat " + os.path.join(path, "samples/sample-sensors.txt"))

    # Check for errors.
    if rc != 0:
        logger.write("Failed to load sensor info.")
        return()

    # Split output by device.
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

    # Parse devices.
    devicen = 0
    for device in devices:
        # Prepare report to recieve device names.
        report["sensors"]["device" + str(devicen)] = {
            "name0" : "",
            "name1" : ""
        }
        i = 0

        # Determine name0.
        while ord(device[i]) != 10:
            report["sensors"]["device" + str(devicen)]["name0"] += device[i]
            i += 1

        # Skip "Adapter: ".
        while device[i] != " ":
            i += 1
        i += 1

        # Determine name1.
        while ord(device[i]) != 10:
            report["sensors"]["device" + str(devicen)]["name1"] += device[i]
            i += 1

        # Parse device data.
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

        # Report values.
        report["sensors"]["device" + str(devicen)]["values"] = values
        devicen += 1

"""
    Load and report memory utilization.
"""
def loadMemory():
    # Load memory stats (works on virts).
    (freeOut, rc) = toOS("free -o | tail -n +2")

    # Check for errors.
    if rc != 0:
        logger.write("Failed to load memory info.")
        return()

    # Parse output.
    report["memory"] = {}
    i = 0
    freeOutLen = len(freeOut)
    while i < freeOutLen:           # until end of file
        # Build name.
        name = ""
        while freeOut[i] != ":":
            name += freeOut[i]
            i += 1
        i += 1

        # Build total.
        total = ""
        while freeOut[i] == " ":    # skip spaces
            i += 1
        while freeOut[i] != " ":
            total += freeOut[i]
            i += 1

        # Build used.
        used = ""
        while freeOut[i] == " ":    #skip spaces
            i += 1
        while freeOut[i] != " ":
            used += freeOut[i]
            i += 1

        # Burn through rest of line.
        while ord(freeOut[i]) != 10:
            i += 1
        i += 1

        # Report data.
        report["memory"][name] = {
            "total": total,
            "used": used,
            "free": str(int(total) - int(used)),
            "utilization": str(round(int(used) / int(total) * 100, 2))
        }

"""
    Load and report logical volume information. Specifically, utilization.
"""
def loadLogicalV():
    # Load logical volume utilization (virts use sample output).
    if not globe["demo"]:
        (dfOut, rc) = toOS("df | tail -n +2")
    else:
        (dfOut, rc) = toOS("cat " + os.path.join(path, "samples/sample-df.txt"))

    # Check for errors.
    if rc != 0:
        logger.write("Failed to load logical volume info.")
        return()

    # Parse output with headers/keys that apply to df and report.
    report["logical_volumes"] = parseLines(dfOut, ["filesystem", "k_blocks", "used", "available", "use_percent", "mount_point"])

"""
    Load and report CPU utilization metrics.
"""
def loadCpu():
    # Load CPU utilization.
    (topOut, rc) = toOS("top -b -n1 | grep Cpu | tr -d '\n'")

    # Check for errors.
    if rc != 0:
        logger.write("Failed to load CPU info.")
        return()

    # Add info to report based on position in string - these values should always be in the same place.
    report["cpu"] = {
        "user": topOut[8:13].replace(" ", ""),
        "system": topOut[17:22].replace(" ", ""),
        "niced": topOut[26:31].replace(" ", ""),
        "idle": topOut[35:40].replace(" ", ""),
        "waiting": topOut[44:49].replace(" ", ""),
        "hw_interrupt": topOut[53:58].replace(" ", ""),
        "sw_interrupt": topOut[62:67].replace(" ", ""),
        "stolen": topOut[71:76].replace(" ", "")
    }

"""
    Creates a nesting map of physical and logical disk and collects relavent info such as size.
    Then SMART values are loaded. All data is added to the report.
"""
def loadDrives():
    # Load drive map and stats (demo mode uses sample output).
    if not globe["demo"]:
        (lsblkOut, lsblkrc) = toOS("lsblk | tail -n +2")
    else:
        (lsblkOut, lsblkrc) = toOS("cat " + os.path.join(path, "samples/sample-lsblk.txt"))

    # Check for errors.
    if lsblkrc != 0:
        logger.write("Failed to load drive map info.")
        return()

    # Parse drive map info.
    report["drives"] = {}
    heritage = []
    lsblkOutLen = len(lsblkOut)
    i = 0                   # i is index in output
    while i < lsblkOutLen:
        j = 0               # j tracks the nexted position of device name
        # Skip over start of line spacing and track nested position.
        while ord(lsblkOut[i]) != 10:
            while not (97 <= ord(lsblkOut[i]) <= 122 or 48 <= ord(lsblkOut[i]) <= 57):
                i += 1
                j += .5
            # Build name.
            name = ""
            while 97 <= ord(lsblkOut[i]) <= 122 or 48 <= ord(lsblkOut[i]) <= 57:
                name += lsblkOut[i]
                i += 1
            # Skip MAJ:MIN an RM headers.
            for x in range(2):
                while lsblkOut[i] == " ":
                    i += 1
                while lsblkOut[i] != " ":
                    i += 1
            while lsblkOut[i] == " ":
                i += 1      # skip spaces
            # Build size.
            size = ""
            while lsblkOut[i] != " ":
                size += lsblkOut[i]
                i += 1
            # Skip RO and Type.
            while lsblkOut[i] == " ":
                i += 1
            while lsblkOut[i] != " ":
                i += 1
            while lsblkOut[i] == " ":
                i += 1
            # Build dtype.
            dtype = ""
            while not ord(lsblkOut[i]) in [10, 32]:
                dtype += lsblkOut[i]
                i += 1
            # Skip newlines and spaces - build mount if applicable.
            while lsblkOut[i] == " " and ord(lsblkOut[i]) != 10:
                i += 1
            mount = ""
            while ord(lsblkOut[i]) != 10:
                mount += lsblkOut[i]
                i += 1

            # Determine where this drive is in the tree.
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
                heritage[len(heritage) - 1] = [name, j]

            # Add info to report.
            parent = report["drives"]
            if j > 0:
                ancestor = report["drives"][heritage[0][0]]
                for x in range(1, len(heritage) - 1):
                    ancestor = ancestor["children"][heritage[x][0]]
                if not "children" in ancestor:
                    ancestor["children"] = {}
                parent = ancestor["children"]
            parent[name] = {
                "size": size,
                "type": dtype,
            }
            if len(mount) > 0:
                parent[name]["mount"] = mount
        i += 1

    # Load, process and report SMART values for all drives.
    headers = ["attr_id", "attribute_name", "flag", "value", "worst", "thresh", "type", "updated", "when_failed", "raw_value"]
    for device in report["drives"]:
        # Ensure device is disk
        if report["drives"][device]["type"] != "disk":
            continue

        # Load SMART info: -H for overal health and -A for SMART attributes (virts use sample output).
        if not globe["demo"]:
            (smartHOut, smartrc) = toOS("smartctl -H /dev/" + device + " | grep result")
            (smartAOut, smartrc) = toOS("smartctl -A /dev/" + device + " | tail -n +8 | head -n -1")
        else:
            (smartHOut, smartrc) = toOS("cat " + os.path.join(path, "samples/sample-smart-H-PASSED.txt"))
            (smartAOut, smartrc) = toOS("cat " + os.path.join(path, "samples/sample-smartA" + device + ".txt"))

            # Check for errors.
            if smartrc != 0:
                logger.write("Failed to load SMART data.")
                return()

        # Add overall health status to report.
        report["drives"][device]["smart_health"] = smartHOut[50:].replace("\n", "")
        # Parse output with headers/keys that apply to SMART attributes and report.
        report["drives"][device]["smart_attributes"] = parseLines(smartAOut, headers)

"""
    Adds running processes to report.
"""
def loadProcesses():
    # Load processes for parsing (works on virts).
    (psOut, rc) = toOS("ps -A | tail -n +2")

    # Check for errors.
    if rc != 0:
        logger.write("Failed to load processes.")
        return()

    # Parse output with headers/keys that apply to ps and report.
    report["processes"] = parseLines(psOut, ["pid", "tty", "time", "cmd"])

"""
    Adds the following data to report: uptime, kernel-version, dmesg
    No special processing is needed for these outputs.
"""
def loadVarious():
    # Report uptime (works on virts).
    (report['uptime'], uprc) = toOS("uptime -p | cut -c 4- | tr -d '\n'")

    # Report kernel-version (works on virts).
    (report["os"], unamerc) = toOS("uname -v | tr -d '\n'")

    # Report dmesg (virts use sample output).
    if not globe["demo"]:
        (report['dmesg'], dmesgrc) = toOS("dmesg | tail -n 200")
    else:
        (report['dmesg'], dmesgrc) = toOS("cat " + os.path.join(path, "samples/sample-dmesg.txt"))

    # Load, but do not process network error info.
    # I am intentionally leaving this part of the report vague and unprocessed for security reasons.
    (report["network"], networkrc) = toOS("ifconfig eth0 | tail -n +4")

    # Check for errors.
    if uprc != 0 or unamerc != 0 or dmesgrc != 0:
        logger.write("Failed to load uptime, kernel-verson, and/or dmesgrc.")

"""
    Takes ([str]lines, [array of strings]headers) and returns an array of objects. These objects have keys from headers, and the
    values are pulled from lines. Lines much be formated with no headers and with space(s) values.
    Run "ps -A | tail -n +2" for an example of an acceptable value for lines.
"""
def parseLines(lines, headers):
    # Initiate return vlaue and template object.
    data = []
    template = {}
    for header in headers:
        template[header] = ""

    # Prepare to extract infro from lines.
    i = 0           # char interator
    linen = 0       # line interator
    lineslen = len(lines)
    while i < lineslen:        # not end of string / for each line

        # Add new object to data.
        data.append(template.copy())

        # For each value in line, skip spaces and store value cooresponding to the header.
        for header in headers:
            while lines[i] == " ":      #skip spaces
                i += 1
            # Build value until a space is reached. A space can be accepted if it is the last value in the line.
            while lines[i] != "\n" and not (header != headers[-1] and lines[i] == " "):
                data[linen][header] += lines[i]
                i += 1
        # Next char and line.
        i += 1
        linen += 1

    return data

"""
    Attempts to send a command to the OS. Accepts a command as a string and returns ([str]output, [int]returncode).
"""
def toOS(command):
    # Attempt to send command to OS.
    try:
        result = subprocess.run(command + " 2>&1", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out = result.stdout.decode('utf-8')
        rc = result.returncode
        if rc == 0:
            logger.write('  Successfully ran: ' + command + '.')
        else:
            logger.write('  OS took command, but there was an issue: ' + command + '.')
        return (out, rc)
    except:
        logger.write('  Host failed to handle :' + command)
        return ("failed", -1)

# Run main once all functions are loaded.
if __name__ == "__main__":
    main(True)