"""
    This file serves as an extention of application.py and provides
    some consolidated functionality for other files in this project.

    This is not intended to be executed independently.
"""

from flask import redirect, render_template, request, session
from functools import wraps
import sqlite3
import configparser
import time
import metrics

"""
    Decorate routes to require login.
    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/

    * Technique implemented from CS50
"""
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

"""
    Stores current user info in session. This may need to run mid-session.
"""
def update_session_vars():
    # Although there is a function in users to get user info, separate code is used here since users imports helpers.
    # TODO check for sql failure
    user_line = to_sql('SELECT * FROM users WHERE "user_id" = "' + str(session["user_id"]) + '"', 'r', "whm.db")['details'][0]
    session["first"] = user_line[3]
    session["last"] = user_line[4]
    session["email"] = user_line[5]
    session["phone"] = user_line[6]
    session["admin"] = user_line[7]
    return

"""
    Takes a config filename as a parameter and returns dictionary of settings.
"""
def get_config(file):
    try:
        # Attempt to read config.
        config = configparser.RawConfigParser()
        config.read(file)
        result = {
            'return': True,
            'max_log_size': config.get('logger', 'max_log_size'),
            'max_log_age_unit': config.get('logger', 'max_log_age_unit'),
            'max_log_age_n': config.get('logger', 'max_log_age_n'),
            'user_str_len': config.get('logger', 'user_str_len'),
            'source_str_len': config.get('logger', 'source_str_len')
        }
    except:
        # Failure - Return.
        result = {
            'return': False,
            'details': "Failed to return config. Config file may need to be recovered. Tried: " + file
        }

    # Read was successful, return settings.
    return result

"""
    Run partial metrics report and update chart_data with timestamped data.
    Accepted "hours", "days", or "weeks" as scope.
"""
def record_metrics(scope):
    # Partial report stored in update.
    update = metrics.main(False, 'metrics-tracker')

    # Load a list of present charts in DB.
    charts = [chart[0] for chart in to_sql('SELECT name FROM sqlite_master WHERE type = "table";', "r", "chart_data.db")]

    # TODO keys=None?
    """
        Write data to DB. table_prefix and scope determine which table.
        table_prefix should look like "section_optionalSubSection_". Ex. "cpu_" or " mem_Swap_".
        table_prefix and data are both strings (data is CSV).
    """
    def record(table_prefix, data, keys=None):
        # Determine table to write to.
        table = table_prefix + "_" + scope

        # If table doesn't exist it is created.
        if not table in charts:
            # Build table creation command and then run it.
            create_table = "CREATE TABLE '" + table + "' ('time' DATETIME"
            for key in keys:
                create_table += ", '" + key + "' NUMERIC"
            create_table += ")"
            to_sql(create_table, 'w', 'chart_data.db')

        # Insert data into table.
        to_sql("INSERT INTO '" + table + "' VALUES (CURRENT_TIMESTAMP" + data + ");" , 'w', 'chart_data.db')

    """
        Prepars data (a dictionary) to be entered into an SQL command.
        Returns (String of CSV as entered in SQL, List of keys to correspond with the CSV).
    """
    def dict_to_sql_part(data):
        # Initiate return values.
        sql_part = ""
        keys = []

        # Iterate through data building return values.
        for key in data:
            sql_part += ', ' + data[key]
            keys.append(key)

        # Return items ready for SQL entry.
        return (sql_part, keys)

    # Proccess and record info for each monitored section.

    # Sensors section.
    for device in update["sensors"]:
        (sens_update, keys) = dict_to_sql_part(update['sensors'][device]['values'])
        record('sens_' + update["sensors"][device]["name0"], sens_update, keys)

    # Mem section.
    for mem_group in update["memory"]:
        (mem_update, keys) = dict_to_sql_part(update['memory'][mem_group])
        record('mem_' + mem_group , mem_update, keys)

    # CPU section.
    (cpu_update, keys) = dict_to_sql_part(update['cpu'])
    record('cpu', cpu_update, keys)

    # Storage section.
    # TODO


    #TODO delete old entries from chart_data. This can be configured in cfg


"""
    Ensures strings are save for SQL entry.
    Returns True if all chars are alphanumeric or one of the following: . _ @
"""
def validate_sql(s):
    # For each char, return False if it is not in acceptable ranges.
    for c in str(s):
        x = ord(c)
        #       .           _          0          9          @  A       Z          a           z
        if x != 46 and x != 95 and not 48 <= x <= 57 and not 64 <= x <= 90 and not 97 <= x <= 122:
            return False
    return True

"""
    General SQL command executor.
    command is a script of SQL to run.
    mode is a script, "w" to write, and "r" to read.
    db is a string to specify the filename of the db.
"""
def to_sql(command, mode, db):
    try:
        # Set up db and cursor.
        db = sqlite3.connect(db)
        crsr = db.cursor()

        # Run command.
        crsr.execute(command)

        # If writing, commit change and return success.
        if mode == 'w':
            db.commit()
            db.close()
            return {
                'success': True,
                'details': 'Write Complete'
            }
        # If reading, return data.
        elif mode == 'r':
            result = crsr.fetchall()
            db.close()
            return {
                'success': True,
                'details': result
            }
        # Neither reading or writing.
        return {
                'success': False,
                'details': 'Bad Mode'
            }
    except:
        # Error occured - Return failure.
        return {
            'success': False,
            'details': "SQL failed: " + command
        }