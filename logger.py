import datetime
import os
import shutil

max_log_size = 145000                       # logs back up at this size (145000 is about 1000 lines)
max_log_age = datetime.timedelta(hours=1)   # logs older than this time will be deleted

class Logger():
    """Manages logging operations"""

    # construct this Logger
    def __init__(self, user, source):
        self.user = user
        self.source = source
        self.path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "logs")

        # logger to track actions from logger.py
        if source != "logger.py":
            self.selfLogger = Logger(user, "logger.py")

        # if ./logs dir doesn't exist, it is created
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    # add event to whm.log
    def write(self, eventin, mode="a", force=False):
        if not force:
            self.checkSize()

        event = eventin.replace("\n", "{NL}")   # removes newline chars from log entries
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # attempt write file operation
        try:
            log = open(os.path.join(self.path, "whm.log"), mode)
            log.write(timestamp + '\t' + self.source + '\t' +self.user + '\t' + event + '\n')
            log.close()
            return 0
        except:
            print("Error: Failed to write to log.")
            return 1

    # overwrites this log
    def clear(self):
        return self.selfLogger.write('Log cleared', 'w', True)

    # copy whm.log to a backup named with date and time
    def backup(self):

        # ensure whm.log existes
        if not os.path.isfile(os.path.join(self.path, "whm.log")):
            return 1

        bak_name = 'whm_bak_' + datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S') + '.log'
        bak_path = os.path.join(self.path, bak_name)

        # ensure backup name doesn't already exist
        # this may occure if this function is called more than once in the same second
        if os.path.isfile(bak_path):
            self.selfLogger.write('Tried to backup whm.log to ' + bak_name + ', but file already existed.')
            return 2

        # attempt file operation
        try:
            shutil.copy(os.path.join(self.path, 'whm.log'), bak_path)
            self.selfLogger.write('whm.log backed up to ' + bak_name)
            return 0
        except:
            return 3

    # backs up and clears old logs for smooth file operations
    def checkSize(self):

        # return if whm.log does not need maintenance
        if os.path.getsize(os.path.join(self.path, "whm.log")) < max_log_size:
            return 0

        # whm.log is too large - backs it up and clears it
        self.selfLogger.write("Max log size reached: " + str(max_log_size) + " - Started new log.", "a", True)
        self.backup()
        self.clear()
        self.selfLogger.write("Max log size reached: " + str(max_log_size) + " - Started new log.")

        # a new back up was create - ensures all backups are within age limits
        now = datetime.datetime.now()
        for filename in os.listdir(self.path):
            filetimestr = ""
            for c in filename:
                if 48 <= ord(c) <= 57:
                    filetimestr += c
            if filetimestr != "":   # for files with numbers in the name
                try:
                    # will pass if numbers are in the correct date format
                    filetimeobj = datetime.datetime.strptime(filetimestr, '%Y%m%d%H%M%S')
                except:
                    # there is a file with numbers in the name but they do not translate to a date - loop next filename
                    self.selfLogger.write("Unexpected item found in log directory: " + filename)
                    continue
                if now - max_log_age > filetimeobj:
                    # file is too old - deletes it
                    os.remove(os.path.join(self.path, filename))
                    self.selfLogger.write("Deleted aged log: " + filename)
