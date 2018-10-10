import datetime
import os
import shutil
import configparser

"""
    Manages logging operations.
    This class allows each user and source to have their own instance in order
    to maintain accountability and to track down errors. File management is taken care of
    here so that over files simply need to create an instance and pass in events to log.
"""
class Logger():

    """
        Construct this Logger.
        Takes the acting user and the source tool or file generating the event. Both are strings.
    """
    def __init__(self, user, source):

        # Load globals from whm.cfg.
        config_success = True
        global max_log_size
        global max_log_age
        try:
            config = configparser.RawConfigParser()
            config.read('whm.cfg')
            max_log_size = config.getint('logger', 'max_log_size')
            max_log_age = datetime.timedelta(**{config.get('logger', 'max_log_age_unit'): config.getint('logger', 'max_log_age_n')})

            user_str_len = config.getint('logger', 'user_str_len')
            source_str_len = config.getint('logger', 'source_str_len')

        except:
            # Failed to read config, setting default values.
            max_log_size = 145000
            max_log_age = datetime.timedelta(hours=1)

            user_str_len = 15
            source_str_len = 12

            config_success = False

        # Load other instance variables.

        """ Trying this section in the block above.
        try:
            user_str_len = config.getint('logger', 'user_str_len')
            source_str_len = config.getint('logger', 'source_str_len')
        except:
            # Failed to read config, setting default values.
            user_str_len = 15
            source_str_len = 12
            config_success = False """

        self.user = (user + (" " * user_str_len))[:user_str_len]
        self.source = (source + (" " * source_str_len))[:source_str_len]
        self.path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "logs")

        # Logger to track actions from logger.py.
        if source != "logger.py":
            self.selfLogger = Logger(user, "logger.py")
            if not config_success:
                self.selfLogger.write("Failed to load vars from config.")

        # If ./logs dir doesn't exist, it is created.
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    """
        Add event to whm.log.
        eventin is the string describing the event.
        mode specifies the method of writing. "a" to append and "w" to overwrite.
        force allows writing regardless of current log size.
    """
    def write(self, eventin, mode="a", force=False):
        # Ensure log is within configured size limits.
        if not force and os.path.isfile(os.path.join(self.path, "whm.log")):
            self.checkSize()

        # Removes newline chars from log entries and get current time.
        event = eventin.replace("\n", "{NL}")
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Attempt write file operation.
        try:
            log = open(os.path.join(self.path, "whm.log"), mode)
            log.write(timestamp + ' ' + self.source + ' ' +self.user + ' ' + event + '\n')
            log.close()
            return 0
        except:
            # Failed - Return.
            print("Error: Failed to write to log.")
            return 1
    """
        Start a new empty log.
    """
    def clear(self):
        return self.selfLogger.write('Log cleared', 'w', True)

    """
        Copy whm.log to a backup named with date and time.
        Pass name if filename was tried and already exists.
    """
    def backup(self, name=None):
        # Ensure whm.log existes.
        if not os.path.isfile(os.path.join(self.path, "whm.log")):
            return 1

        # Determine new filename and its path.
        if name == None:
            bak_name = 'whm_bak_' + datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S') + '.log'
            bak_path = os.path.join(self.path, bak_name)
        else:
            # Tack an 'a' to the end of the filename and try again.
            bak_name = name[:-4] + 'a.log'
            bak_path = os.path.join(self.path, bak_name)

        # Ensure backup name doesn't already exist.
        # This may occure if this function is called more than once in the same second.
        if os.path.isfile(bak_path):
            # Try again with an 'a' appended to file name.
            return self.backup(bak_name)

        # Attempt file operation to copy the current log to the new file.
        try:
            shutil.copy(os.path.join(self.path, 'whm.log'), bak_path)
            self.selfLogger.write('whm.log backed up to ' + bak_name)
            return 0
        except:
            return 3
    """
        Return all text in the active log by default as well as the available logs.
        Optionally, provide a logname to get its text.
    """
    def get_logs(self, logname='whm.log'):
        # Try file operation to read log and OS operation to list the log directory contents.
        try:
            log = open(os.path.join(self.path, logname))
            log_text = log.read()
            log.close()
            files = sorted(os.listdir(self.path), reverse=True)
            files.insert(0, files.pop())
            return {
                'log_text': log_text,
                'log_files': files
            }
        except:
            return 'Failed to read logs...'

    """
        Backs up and clears old logs as configured to ensure smooth file operations.
    """
    def checkSize(self):
        # Return if whm.log does not need maintenance.
        if os.path.getsize(os.path.join(self.path, "whm.log")) < max_log_size:
            return 0

        # whm.log is too large - backs it up and clears it.
        self.selfLogger.write("Max log size reached: " + str(max_log_size) + " - Started new log.", "a", True)
        self.backup()
        self.clear()
        self.selfLogger.write("Max log size reached: " + str(max_log_size) + " - Started new log.")

        # A new back up was create - Ensures all backups are within age limit.
        now = datetime.datetime.now()
        for filename in os.listdir(self.path):
            # Parse established time from filename in format YYYYMMDDHHMMSS
            filetimestr = ""
            for c in filename:
                if 48 <= ord(c) <= 57:
                    filetimestr += c

            # Ensure non-empty string. Current logfile will be skipped here.
            if filetimestr != "":
                try:
                    # Will pass if numbers are in the correct date format.
                    filetimeobj = datetime.datetime.strptime(filetimestr, '%Y%m%d%H%M%S')
                except:
                    # There is a file with numbers in the name but they do not translate to a date - loop next filename
                    self.selfLogger.write("Unexpected item found in log directory: " + filename)
                    continue

                # If file is too old, it is deleted.
                if now - max_log_age > filetimeobj:
                    os.remove(os.path.join(self.path, filename))
                    self.selfLogger.write("Deleted aged log: " + filename)
