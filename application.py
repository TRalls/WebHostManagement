#!/usr/bin/env python3
"""
    See README.txt for info on fuctionality of this webapp. This file serves as the access point for client
    side scripts to interact of WHM functions. Some of these functions can alternatively be accessed via WHM
    CLI tools if the user has access to the systems CLI.

    In general, form validation is done in browser to reduce unproductive network traffic and server processing.
    However, redundant validation is done here as well in case POST is sent to these URLs in some manner
    other than the supplied client-side files allow.

    Some user-accessed URLs lack POST handling even though these pages send requests for more information or
    some action to be taken. This is because the format in which this information and these actions are requested
    is not unique to any specific user-accessed URL. In these cases, the client side scripts send requests to POST
    only URLs that are capable of accommodating the needs of more than one user-accessed URL.

    Run this file to start the application with python 3.5+.
"""

from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
import configparser
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from logger import Logger
from helpers import *
import users
import metrics

# Aspects of this app setup were borrowed from CS50, including the application and session configuration.

# Configure application.
app = Flask(__name__, static_url_path='/static')

# Configure session to use filesystem (instead of signed cookies).
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Use to read and write notable events.
logger = Logger("Unknown", "WebApp")

"""
    To be ran once, when the webapp is first accessed.
"""
@app.before_first_request
def before_first_request():
    # Load record keeping config settings
    load_record_conf()

    # Schedule recording of metrics for charting.
    # https://stackoverflow.com/questions/21214270/scheduling-a-function-to-run-every-hour-on-flask
    scheduler = BackgroundScheduler()
    scheduler.start()
    # Job intervals below may be adjusted to display functionality. However, code assumes the values shown in comments at the end of the lines.
    scheduler.add_job(
        func=record_metrics,
        args=["hours"],
        trigger=IntervalTrigger(minutes=1), # hours=1 (May use other values for testing.)
        id='hourly_metrics',
        name='Records current metrics on an hourly scope',
        replace_existing=True)
    scheduler.add_job(
        func=record_metrics,
        args=["days"],
        trigger=IntervalTrigger(hours=1), # days=1
        id='daily_metrics',
        name='Records current metrics on a daily scope',
        replace_existing=True)
    scheduler.add_job(
        func=record_metrics,
        args=["weeks"],
        trigger=IntervalTrigger(hours=2), # weeks=1
        id='weekly_metrics',
        name='Records current metrics on a weekly scope',
        replace_existing=True)
    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())

"""
    Homepage shows overview of general metrics and tasks.
"""
@app.route("/")
@login_required
def home():
    return render_template("home.html")

"""
    Send template for CPU metrics. JS will display info from session storage and from AJAX requests.
"""
@app.route("/cpu")
@login_required
def cpu():
    return render_template("cpu.html")

"""
    Displays dmesg logs and, if user is an admin, whm logs (logged by this app).
"""
@app.route("/logs")
@login_required
def logs():
    if request.args.get('action') == "get_whm_logs":
        if session['admin']:
            # WHM logs requested and user is an admin. Return whm.log (current log) if no other log is specified.
            logname = request.args.get('logname')
            if not logname:
                logname = 'whm.log'
            return jsonify({
                'return': session['logger'].get_logs(logname)
            })
        else:
            # None admin tried to pull whm logs. Deny access and log event.
            session['logger'].write("Non-admin tried: " + request.args.get('action'))
            return jsonify({
                'return': {
                    'log_text': 'Access denied...'
                }
            })
    else:
        # Webpage requested, return page.
        return render_template("logs.html")

"""
    Send template for memory metrics. JS will display info from session storage and from AJAX requests.
"""
@app.route("/memory")
@login_required
def memory():
    return render_template("memory.html")

"""
    Send template for network metrics. JS will load data from session storage.
"""
@app.route("/network")
@login_required
def network():
    return render_template("network.html")

"""
    Send template to display processes. Additional functionality is provided by JS and other functions.
"""
@app.route("/processes")
@login_required
def processes():
    return render_template("processes.html")

"""
    Send template for sensors metrics. JS will display info from session storage and from AJAX requests.
"""
@app.route("/sensors")
@login_required
def sensors():
    return render_template("sensors.html")

"""
    Display available settings and handle changes to them.
    POST is used for everything besides initially requesting the webpage.
    In a POST request, action is used to route request handling.
"""
@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        if request.form.get('action') in ["update", "other_update"]:
            # Update user information. other_update specifies updating another users info and requires admin rights.
            if request.form.get('action') == "other_update":
                if not session['admin']:
                    # Non-admin tried to update another users' info. Log and deny access.
                    session['logger'].write("Non-admin tried: " + request.form.get('action'))
                    return jsonify({
                        'return': False,
                        'details': "Unauthorized Access"
                    })
                # Other user is being updated by admin - Remember subject user id.
                user_id = request.form.get('user_id')
            else:
                # User is updating their own info.
                # If a new password is provided, ensure current password was entered and is correct. Duel password entry is ensured on client side.
                if request.form.get('npassword'):
                    selection = users.getUser("user_id", session["user_id"])
                    if not selection['return'] or not pwd_context.verify(request.form.get("password"), selection['user'][2]):
                        return jsonify({
                            'return': False,
                            'details': "Incorrect current password entered."
                        })

                # Proceed with update request, remember subject (current) user id.
                user_id = session['user_id']

            # Store new password as a hash if provided, otherwise it hash will be stored as an empty string.
            if request.form.get('npassword'):
                newHash = pwd_context.hash(request.form.get('npassword'))
            else:
                newHash = ""

            # This holds the user id to update and everything that can be updated. Empty strings indicate fields that should remain unchanced.
            update_bundle = [
                user_id,
                newHash,
                request.form.get('first'),
                request.form.get('last'),
                request.form.get('email'),
                request.form.get('phone')
            ]

            # Attempt to update though users' update handler.
            result = users.updateUser(update_bundle)

            if result['return'] == True:
                # Update was successful - Log and return.
                update_return = update_session_vars()
                # Check if session vars updated successfully.
                if not update_return['success']:
                    return jsonify({
                        'return': False,
                        'details': "User information updated, but there was an issue reading the updated info."
                    })
                session['logger'].write("Update with info: " + str(update_bundle))
                return jsonify({
                    'return': True,
                    'details': "User information updated."
                })
            else:
                # Update was unsuccessful - Log and return edetails.
                session['logger'].write("Failed to update with info: " + str(update_bundle))
                return jsonify(result)

        # Settings actions below this point require admin rights. Ensure privilege before moving forward.
        if not session['admin']:
            session['logger'].write("Non-admin tried: " + request.form.get('action'))
            return jsonify({
                'return': False,
                'details': "Session by admin required"
            })

        # Returns a table of users or requested users.
        if request.form.get('action') == "get_table":
            # Validate requested table.
            if not request.form.get("table") in ["users", "requests"]:
                return jsonify({
                    'reported': False,
                    'details': "Invalide table"
                })
            # Get and return data.
            return jsonify({
                'reported': True,
                'lines': users.getUsers(group=request.form.get("table"))
            })

        # Returns the current log settings.
        if request.form.get('action') == "get_config":
            return jsonify(get_config('whm.cfg'))

        # Sets log settings
        if request.form.get('action') == "set_config":
            if request.form.get('section') == "log":
                # Load defaults from backup config if defaults are requested, or load settings from the form.
                if int(request.form.get('log_default_flag')) == 1:
                    settings = get_config('whm.cfg.bak')
                    # Ensure backup config was loaded.
                    if not settings['return']:
                        session['logger'].write(settings['details'])
                        return jsonify(settings)
                else:
                    settings = {
                        'max_log_size': request.form.get('max_size'),
                        'max_log_age_unit': request.form.get('max_age_unit'),
                        'max_log_age_n': request.form.get('max_age_n'),
                        'user_str_len': request.form.get('usr_len'),
                        'source_str_len': request.form.get('src_len')
                    }

                # Ensure max_log_size is within range. Errors may occur outside of this range.
                if settings['max_log_size']:
                    try:
                        x = int(settings['max_log_size'])
                        if not 5000 <= x <= 1000000000:
                            raise Exception()
                    except:
                        return jsonify({
                            'return': False,
                            'details': "Invalid Maximum Log File Size"
                        })

                # Ensure valid age unit.
                if not settings['max_log_age_unit'] in ['minutes', 'hours', 'days', 'weeks']:
                    return jsonify({
                        'return': False,
                        'details': "Invalid Maximum Archive Age Unit"
                    })

                # Ensure age is a non-neg whole number.
                if settings['max_log_age_n']:
                    try:
                        x = int(settings['max_log_age_n'])
                        if not 0 <= x:
                            raise Exception()
                    except:
                        return jsonify({
                            'return': False,
                            'details': "Invalid Maximum Archive Age"
                        })

                # Ensure user_str_len is in acceptable range.
                if settings['user_str_len']:
                    try:
                        x = int(settings['user_str_len'])
                        if not 0 <= x <= 50:
                            raise Exception()
                    except:
                        return jsonify({
                            'return': False,
                            'details': "Invalid User Length"
                        })

                # Ensure source_str_len is in acceptable range.
                if settings['source_str_len']:
                    try:
                        x = int(settings['source_str_len'])
                        if not 0 <= x <= 50:
                            raise Exception()
                    except:
                        return jsonify({
                            'return': False,
                            'details': "Invalid Source Length"
                        })

                # Attempt to write each setting to config.
                try:
                    config = configparser.RawConfigParser()
                    config.read('whm.cfg')
                    for var in ['max_log_size', 'max_log_age_unit', 'max_log_age_n', 'user_str_len', 'source_str_len']:
                        if settings[var]:
                            config.set('logger', var, settings[var])
                    with open('whm.cfg', 'w') as configfile:
                        config.write(configfile)
                except:
                    return jsonify({
                        'return': False,
                        'details': "Failed to write config."
                    })

                # Log and return success.
                session["logger"].write("Log config changed")
                return jsonify({
                    'return': True,
                    'details': "Function ran with no errors."
                })

		    # Sets record settings
            if request.form.get('section') == "record":
                # Load defaults from backup config if defaults are requested, or load settings from the form.
                if int(request.form.get('record_default_flag')) == 1:
                    settings = get_config('whm.cfg.bak')
                    if not settings['return']:
                        # Ensure backup config was loaded.
                        session['logger'].write(settings['details'])
                        return jsonify(settings)
                else:
                    settings = {
                        'hours_age_max': request.form.get('record_hours'),
                        'days_age_max': request.form.get('record_days'),
                        'weeks_age_max': request.form.get('record_weeks')
                    }

                # Ensure all fields are whole numbers between 0 and 500.
                for field in ['hours_age_max', 'days_age_max', 'weeks_age_max']:
                    if settings[field]:
                        try:
                            x = int(settings[field])
                            if not 0 <= x <= 500:
                                raise Exception()
                        except:
                            return jsonify({
                                'return': False,
                                'details': "Values must be whole numbers between 0 and 500."
                            })

                # Attempt to write each setting to config.
                try:
                    config = configparser.RawConfigParser()
                    config.read('whm.cfg')
                    for var in ['hours_age_max', 'days_age_max', 'weeks_age_max']:
                        if settings[var]:
                            config.set('record', var, settings[var])
                    with open('whm.cfg', 'w') as configfile:
                        config.write(configfile)
                    # Load new config settings
                    load_record_conf()
                except:
                    return jsonify({
                        'return': False,
                        'details': "Failed to write config."
                    })

                # Log and return success.
                session["logger"].write("Log config changed")
                return jsonify({
                    'return': True,
                    'details': "Function ran with no errors."
                })

        # User table actions - Requests can be accepted or declined, and current users can be deleted or have admin rights toggled.
        # Requests are handled by users.py and actions are logged.
        if request.form.get('action') == "accept":
            if not users.accept(request.form.get('request_id')):
                session['logger'].write("Failed to accept user with id: " + request.form.get('request_id'))
                return jsonify({
                    'return': False,
                    'details': "Failed to accept user."
                })
        # User action handling.
        if request.form.get('action') == "decline":
            users.delReq(request.form.get('request_id'))
            session['logger'].write("Deleted request with id: " + request.form.get('request_id'))
        if request.form.get('action') == "delete":
            users.delete(request.form.get('request_id'))
            session['logger'].write("Deleted user with id: " + request.form.get('request_id'))
        if request.form.get('action') == "toggle":
            users.toggleAdmin(request.form.get('request_id'))
            session['logger'].write("Toggles admin rights for user id: " + request.form.get('request_id'))

        # Return with no errors.
        return jsonify({
            'return': True,
            'details': "Success"
        })
    else:
        # GET request, return template.
        return render_template("settings.html")

"""
    Send template for storage metrics. JS will display info from session storage and from AJAX requests.
"""
@app.route("/storage")
@login_required
def storage():
    return render_template("storage.html")

"""
    Handing login functionality.
    GET returns webpage, POST attempts to login.
"""
@app.route("/login", methods=["GET", "POST"])
def login():
    # Clear any active session.
    session.clear()

    # Attempt login.
    if request.method == "POST":

        # Ensure form completion.
        if not request.form.get("password") or not request.form.get("username"):
            return jsonify({
                'success': False,
                'details': "Missing username and/or password."
            })

        # Make sure input is safe for SQL.
        if not validate_sql(request.form.get("username")):
            return jsonify({
                'success': False,
                'details': "Unallowed characters enters."
            })

        # Pull user info from DB.
        selection = users.getUser("username", request.form.get("username"))

        # Validate credentials.
        if not selection['return'] or not pwd_context.verify(request.form.get("password"), selection['user'][2]):
            return jsonify({
                'success': False,
                'details': "Bad username and/or password"
            })

        # Set session variables.
        session["user_id"] = selection['user'][0]
        session["username"] = selection['user'][1]
        update_return = update_session_vars()   # vars that may be dynamic
        # Check if session vars updated successfully.
        if not update_return['success']:
            return jsonify({
                'return': False,
                'details': "User logged in but there was an issue loading session variables."
            })


        # Setup logging for this user.
        session["logger"] = Logger(session["username"], "WebApp");
        session["logger"].write(session["username"] + " logged in.")

        # Success
        return jsonify({
            'success': True,
            'details': "Session granted."
        })

    else:
        # GET request, return template.
        return render_template("login.html")

"""
    Clears session and turns user to login page.
"""
@app.route("/logout")
def logout():
    session['logger'].write("Logged out")
    session.clear()
    return redirect("/login")

"""
    Handles requests for user registration.
    GET returns the webpage, POST submits user request.
"""
@app.route("/register", methods=["GET", "POST"])
def register():
    # Clear any active sesssion.
    session.clear()

    # POST - Incoming user registration request.
    if request.method == "POST":
        # Load form data.
        user_request = [
            request.form.get("username"),
            request.form.get("password"),
            request.form.get("first"),
            request.form.get("last"),
            request.form.get("email"),
            request.form.get("phone")
        ]

        # Log event.
        logger.write("Registration attempt: " + str(user_request[0]) + " {pw} " + str(user_request[2:]))

        # Verify complete fields and safe sql.
        for i in range(len(user_request)):
            if not len(user_request[i]) > 0:
                return jsonify({
                    'accepted': False,
                    'details': "One or more fields are empty."
                })
            if not validate_sql(user_request[i]) and i != 1:
                return jsonify({
                    'accepted': False,
                    'details': "Unallowed characters enters."
                })

        # Check if username is in use.
        if users.getUser("username", user_request[0])["return"]:
            return jsonify({
                'accepted': False,
                'details': "Username is already taken. Please try another."
            })

        # Check if username has already been requested.
        if not len(to_sql("SELECT * FROM requests WHERE username = '" + user_request[0] + "'", "r", "whm.db")['details']) == 0:
            return jsonify({
                'accepted': False,
                'details': "Username is already requested. Please try another."
            })

        # Validate password.
        user_request[1] = pwd_context.hash(user_request[1])
        if not pwd_context.verify(request.form.get("vpassword"), user_request[1]):
            return jsonify({
                'accepted': False,
                'details': "Passwords don't match."
            })

        # Attempt to add request to db.
        if not to_sql("INSERT INTO requests VALUES (NULL, " + str(user_request)[1:-1] + ");", "w", "whm.db")['success']:
            return jsonify({
                'accepted': False,
                'details': "Entries were validate, but adding the request to the database failed."
            })

        # All inputs are valid and write to database was successful.
        logger.write("Request submitted")
        return jsonify({
            'accepted': True,
            'details': "Request was submitted to the database."
        })

    else:
        # GET request, return template.
        return render_template("register.html")

"""
    Returns current metrics report.
"""
@app.route("/getReport")
@login_required
def getReport():
    return jsonify({
        'reported': True,
        'report': metrics.main(True, session['username'])
    })

"""
    Limited access to system command line to carry out approved system action. command is built based on request parameters.
"""
@app.route("/command", methods=["POST"])
@login_required
def command():
    # To be used by admins only. Validate access.
    if not session['admin']:
        session['logger'].write("Non-admin tried access OS command url.")
        return jsonify({
            'return': False,
            'details': "Unauthorized Access"
        })

    # Actions available from processes URL.
    if request.form.get('source') == 'processes':
        # Validate pid.
        if not request.form.get('pid').isdigit():
            return jsonify({
                'return': False,
                'details': "Invalid pid: " + request.form.get('pid')
            })
        # Set command based on request parameters.
        if request.form.get('action') == 'hang':
            command = "kill -1 " + request.form.get('pid')
        elif request.form.get('action') == 'kill':
            command = "kill -9 " + request.form.get('pid')
        else:
            # Action not available.
            return jsonify({
                'return': False,
                'details': "Invalid action: " + request.form.get('action')
            })

    # Action to restart.
    if request.form.get('action') == 'restart':
        command = "restart -r now"

    # Log the command that resulted from the request parameters.
    session["logger"].write("Running command: " + command)

    # Run command and return result.
    result = metrics.toOS(command)
    if result[1] != 0:
        # Error
        return jsonify({
            'return': False,
            'details': result[0]
        })
    else:
        # Success
        return jsonify({
            'return': True,
            'details': 'OS executed command without error.'
        })

"""
    Access data in chart_data where some metrics are recorded over time.
"""
@app.route("/chart_data", methods=["POST"])
@login_required
def chart_data():

    # Initiate return value.
    result = {}

    # Note the target_table. If no scale is supplied, default to hours.
    if not request.form.get('scale'):
        scale = 'hours'
    else:
        scale = request.form.get('scale')
    target_table = request.form.get('data_set') + "_" + scale

    # Validate SQL to by seeing if target_table is in the db.
    tables = [chart[0] for chart in to_sql('SELECT name FROM sqlite_master WHERE type = "table";', "r", "chart_data.db")['details']]
    if not target_table in tables:
        session['logger'].write('Failed to read from table. Scope might not be available yet.')
        session['logger'].write('Table name: ' + target_table)
        return jsonify({
            'success': False,
            'data': 'Table does not exist.'
        })

    # If historical data is requested.
    if request.form.get('data_needed') == 'history':

        # Pull table lines based on parameters.
        lines = to_sql("SELECT * FROM '" + target_table + "';", "r", "chart_data.db")
        (result['data'], result['success']) = (lines['details'], lines['success'])

    # If key keys are needed from DB headers.
    if request.form.get('data_needed') == 'keys':
        # Determine key order from DB - SQL validated at start of function.
        table_layout = to_sql("PRAGMA table_info('" + target_table + "');", "r", "chart_data.db")
        result['keys'] = []
        for field in table_layout['details']:
            # Index 1 stores name of the header
            if field[1] != 'time':
                result['keys'].append(field[1])
        result['success'] = table_layout['success']

    if result['success']:
        # Success, return data.
        return jsonify(result)
    else:
        # Failure - Return.
        return jsonify({
            'success': False,
            'data': 'SQL failed to run.'
        })

if __name__ == '__main__':
    port_n = get_config('whm.cfg')['port_n']
    app.run(host="0.0.0.0", port=port_n)