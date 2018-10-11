#!/usr/bin/env python3
"""
    This tool handles all activing regarding user management and can either be used
    from the CLI or from other files in this project. A user running from the CLI will
    have full and anonymous rights to the user database. However, when used from other
    tools, end users will only have access to what those tools allow. Access to these
    functions should be handled with security in mind.

    New users cannot completely register from the webapp. They can request access while
    submitting their registration information. These requests can either be managed
    by an admin from the webapp, or from a user of the command line version of this tool.
"""

import sqlite3
import os
import getpass
from logger import Logger
from helpers import to_sql, validate_sql
from passlib.apps import custom_app_context as pwd_context

# Globals.
logger = Logger("CLI-User", "users.py")
cli = False

"""
    Runs if executed from the CLI.
"""
def main():
    # Create whm.db to track users and requesters if it doesn't exits. This unblockes the web interface.
    if not os.path.exists(os.path.join(os.path.abspath(os.path.dirname(__file__)), "whm.db")):
        os.mknod(os.path.join(os.path.abspath(os.path.dirname(__file__)), "whm.db"))
        if not to_sql(
            "CREATE TABLE 'requests' ('id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 'username' TEXT NOT NULL, 'pw' TEXT NOT NULL, 'first' TEXT NOT NULL, 'last' TEXT NOT NULL, 'email' TEXT NOT NULL, 'phone' TEXT NOT NULL)",
            "w",
            "whm.db"
        )['success']:
            print("Failed to create requests table")
        if not to_sql(
            "CREATE TABLE 'users' ('user_id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,'username' TEXT NOT NULL, 'pw' TEXT NOT NULL, 'first' TEXT NOT NULL, 'last' TEXT NOT NULL, 'email' TEXT NOT NULL, 'phone' TEXT NOT NULL, 'su' BOOLEAN NOT NULL)",
            "w",
            "whm.db"
        )['success']:
            print("failed to create users table")
        logger.write('whm.db initialized.')

    # Remember CLI and welcome user.
    cli = True
    print("\n\nWelcome to the WHM user management CLI!\n")

    # Make first user if needed.
    first_user()

    # Present an option to review requests if requests are present.
    requestCount = len(getUsers(group="requests"))
    if requestCount > 0:
        print("There are " + str(requestCount) + " new user registration request(s).")
        if input("Review them now? Y/N: ") in ["Y", "y"]:
            reviewRequests()
        else:
            print("")
    else:
        print("No new user registration requests.\n")

    mainMenu()

"""
    Main menu loop
"""
def mainMenu():
    # Ensure users exist
    first_user()

    # Menu test and input.
    print("WHM User Management Menu:")
    print("1. Display Users")
    print("2. Add User")
    print("3. Toggle User Permissions")
    print("4. Delete User")
    print("5. Change Password")
    print("6. Review Requests")
    print("7. Exit")
    ans = input("Enter Selection: ")

    # Menu logic - Parameters indicate that target users need to be identified.
    if ans == "1":
        printUsers()
    elif ans == "2":
        add([])
    elif ans == "3":
        toggleAdmin(-1)
    elif ans == "4":
        delete(-1)
    elif ans == "5":
        newPassword(-1)
    elif ans == "6":
        reviewRequests()
    elif ans == "7":
        print("\nGoodbye.\n")
        exit()
    else:
        print("\nUnrecognized option...\n")
    mainMenu()

"""
    If no users exist, one is created through prompt input.
    This user will be an admin.
"""
def first_user():
    if len(getUsers(group="users")) == 0:
        print("There are no users currently registered. Please register the first user.")
        print("\tPlease note that this user will have complete admin rights to WHM.")
        print("\tThis includes user management tasks through the web interface.\n")
        add([])

        # Ensure first user was created.
        users = getUsers(group="users")
        if len(users) == 1:
            toggleAdmin(users[0][0])
        else:
            print("Error adding first user...")
            exit()

"""
    Delete user from database
"""
def delete(user_id):
    # User need to be specified.
    if user_id == -1:
        printUsers()
        print("Enter the User ID of the user that should be deleted.")
        user_id = input("User ID: ")

    # Validate user_id for sql.
    if not validate_sql(user_id):
        print("\nBad SQL - Enter only alphanumeric chars or '.' or '@'.\n")
        return

    # Attempt to interact with db.
    if to_sql("DELETE FROM users WHERE user_id = " + str(user_id), "w", "whm.db")['success']:
        if cli:
            print("\nIf user id existed, it has been deleted.\n")
            logger.write("If user id existed, it has been deleted - user_id: " + str(user_id))
    else:
        if cli:
            print("\nFailed to delete specifed user...\n")
            logger.write("Failed to delete user - user_id: " + str(user_id))

"""
   If user has admin rights, they are removed.
   If user does not have admin rights, they are added.
"""
def toggleAdmin(user_id):
    # User needs to be specified.
    if user_id == -1:
        printUsers()
        print("Enter the User ID of the user that should have admin rights changed.")
        user_id = input("User ID: ")

    # Finds user by id.
    target = [-1]
    try:
        for user in getUsers(group="users"):
            if user[0] == int(user_id):
                target = user
    except:
        print("\nBad User ID...\n")
        return

    # Validate user was found.
    if target[0] == -1:
        if cli:
            print("\nInvalid User ID\n")
            return

    # 1 is made 0 and 0 is made 1.
    admin = abs(target[7] - 1)

    # Attempt to update db.
    if to_sql("UPDATE users SET su = " + str(admin) + " WHERE user_id = " + str(user_id), "w", "whm.db")['success']:
        if cli:
            if admin == 1:
                print("\nUser has been made an admin and has full access from the web interface.\n")
            else:
                print("\nUser has had admin rights removed.\n")
            logger.write("Toggled Admin Rights - user_id: " + str(user_id) + ", Admin: " + str(admin))
    else:
        if cli:
            logger.write("Failed to toggle admin rights - user_id: " + str(user_id) + ", Admin: " + str(admin))

"""
    Registers a new user.
    User is a list of user details. It is built here if no user is provided.
"""
def add(user):
    # No info provided, collect it from CLI.
    if len(user) == 0:
        print("\nPlease enter new user details. Use only alpha-numeric and '@' and '.'.\n")
        # Loop until user name is accepted.
        while len(user) == 0:
            attempt = input("Desired Username: ")
            # Validate input for sql.
            if not validate_sql(attempt):
                print("\tBad SQL - Enter only alphanumeric chars or '.' or '@'.")
                continue # next while
            # Add username to user if it is available.
            if not getUser("username", attempt)["return"]:
                user.append(attempt)
            else:
                print("\tUsername is already in use. Please try another.")
        # Add a password hash to user.
        user.append(getHash())

        # Load user with Firt Name, Last Name, Email, and Phone while validating input is safe for sql.
        while len(user) < 3:
            fn = input("First Name: ")
            if not validate_sql(fn):
                print("\tBad SQL - Enter only alphanumeric chars or '.' or '@'.")
                continue
            user.append(fn)
        while len(user) < 4:
            ln = input("Last Name: ")
            if not validate_sql(ln):
                print("\tBad SQL - Enter only alphanumeric chars or '.' or '@'.")
                continue
            user.append(ln)
        while len(user) < 5:
            em = input("Email: ")
            if not validate_sql(em):
                print("\tBad SQL - Enter only alphanumeric chars or '.' or '@'.")
                continue
            user.append(em)
        while len(user) < 6:
            ph = input("Phone: ")
            if not validate_sql(ph):
                print("\tBad SQL - Enter only alphanumeric chars or '.' or '@'.")
                continue
            user.append(ph)

    # Add 0 indicating none admin by default.
    user.append(0)

    # Attempt to update db.
    if getUser("username", user[0])["return"]:
        return ("Failed", "Username is already in use. Requester should resubmit.")
    if to_sql("INSERT INTO users VALUES (NULL, " + str(user)[1:-1] + ");", "w", "whm.db")['success']:
        if cli:
            print("\nUser has been added and can now access the web interface.\n")
            logger.write("User added - " + user[0])
        return ("Success", "")
    else:
        logger.write("Failed to add user - " + user[0])

"""
    Update user info in db with the info provided.
    info should be a list with fields in the same order as stored in the db excluding user_id.
    Blank fields are not changed in the db.
"""
def updateUser(info):
    # Attempt load current user information into target.
    target = [-1]
    for user in getUsers():
        if user[0] == int(info[0]):
            target = user
    if target[0] == -1:
        # This indicates a failure.
        return -1

    # For each index in target excluding user_id, username, and admin:
    for i in range(2, 7):
        # Set blank info positions to the current value from the db.
        if not info[i - 1]:
            info[i - 1] = target[i]
        # Check sql safety except if working on password. Passwords hashes may have non-standard chars.
        elif i != 2:
            if not validate_sql(info[i - 1]):
                return {
                    'return': False,
                    'details': "Input failed sql validation."
                }

    # Attempt to run update with sql and return result.
    if to_sql("UPDATE users SET pw = '" + info[1] + "', first = '" + info[2] + "', last = '" + info[3] + "', email = '" +
    info[4] + "', phone = '" + info[5] + "' WHERE user_id = '" + str(info[0]) + "'", "w", "whm.db")['success']:
        return {
            'return': True,
            'details': "User information updated."
        }
    else:
        return {
            'return': False,
            'details': "Sql failed to run."
        }

"""
    Reset user password.
    Only runs from CLI.
"""
def newPassword(user_id):
    # Specify user for new password.
    printUsers()
    print("Enter the User ID of user that needs a new password.")
    user_id = input("User ID: ")
    #Validate user exists (if user exists, it should also be safe for sql)
    user_exists = False
    try:
        for user in getUsers(group="users"):
            if user[0] == int(user_id):
                user_exists = True
    except:
        print("\nBad User ID\n")
        return
    if not user_exists:
        print("\nInvalid User ID...\n")
        return

    # Attempt to update db.
    if to_sql("UPDATE users SET pw = '" + getHash() + "' WHERE user_id = " + str(user_id), "w", "whm.db")['success']:
        print("\nPassword updated.\n")
    else:
        print("\nFailed to update password.\n")

"""
    Get password from user, verify it, and return its hash.
"""
def getHash():
    phash = pwd_context.hash(getpass.getpass("Set Password: "))
    if not pwd_context.verify(getpass.getpass("Verify Password: "), phash):
        print("\tPasswords do not match. Please try again...")
        return getHash()
    return phash

"""
    Dispay users in a format that is easy to read.
    Pass in table name for anything other than the "users" table. ("requests")
"""
def printUsers(group="users"):
    # Build text table starting with headers.
    print("\nUser ID  Username        First Name      Last Name       Email                  Phone           Admin")
    print("-------------------------------------------------------------------------------------------------------")

    # For each user, print a line.
    for user in getUsers(group=group):
        # For each field in user info (except pw hash), print it on the line with correct spacing.
        for i in range(8):
            # Set spacing for each column.
            if i == 0:          # user_id
                spacing = 9
            elif i == 5:        # email
                spacing = 23
            else:               # default
                spacing = 16

            # For feilds that are not the hash or the admin toggle, print values with spacing.
            if i not in [2, 7]:
                print((str(user[i]) + (" " * spacing))[:spacing], end="")
            # Convert 1/0 toggle to YES/NO.
            elif i == 7:
                if user[i] == 1:
                    print("YES")
                else:
                    print("NO")
    print("")

"""
    List requests and allows them to be accepted or declined.
"""
def reviewRequests():
    # Check if there are no requests.
    if len(getUsers(group="requests")) == 0:
        print("\nNo current user requests\n")
        return

    # Display requests and prompt for selection.
    print("\nCurrent requests:")
    printUsers(group="requests")
    reqId = input("Select User ID ('M' for Main Menu): ")
    if reqId in ["M", "m"]:
        print("")
        return

    # Validate selection.
    request_exists = False
    for request in getUsers(group="requests"):
        if str(request[0]) == reqId:
            request_exists = True
    if not request_exists:
        print("\nInvalid User ID...\n")
        reviewRequests()
        return

    # Request options.
    print("\nOptions:")
    print("1. Decline")
    print("2. Accept")
    print("3. Main Menu")
    ans = input("Action: ")

    # Option logic.
    if ans == "1":
        delReq(reqId)
    elif ans == "2":
        accept(reqId)
    elif ans == "3":
        print("")
        return
    else:
        print("\nInvalid Action...\n")
        reviewRequests()
        return

    # Continue reviewing.
    reviewRequests()

"""
    Remove request from DB by id.
"""
def delReq(reqId):
    # Validate input is sql safe.
    if not validate_sql(reqId):
        print("Bad SQL - Enter only alphanumeric chars or '.' or '@'.")
        return

    # Attempt to remove request from db.
    if to_sql("DELETE FROM requests WHERE id = " + str(reqId), "w", "whm.db")['success']:
        if cli:
            print("\nRequest has been removed.\n")
    else:
        if cli:
            print("\nFailed to remove request\n")

"""
    Moves line by id from requests to users.
"""
def accept(reqId):
    # Validate input is sql safe.
    if not validate_sql(reqId):
        print("Bad SQL - Enter only alphanumeric chars or '.' or '@'.")
        return False

    # Add user with fields from request line minus the id field.
    newUser = []
    request = to_sql("SELECT * FROM requests WHERE id = " + str(reqId), "r", "whm.db")['details'][0]
    for field in request:
        newUser.append(field)
    del newUser[0]
    add_response = add(newUser)

    # Option if add failed.
    if add_response[0] == "Failed":
        print("\n" + add_response[1])
        if not cli:
            return False
        if input("Would you like to remove the failed request? Y/N: ") in ["y", "Y"]:
            delReq(reqId)
        else:
            return False

    # If add was successful, request is deleted.
    elif add_response[0] == "Success":
        delReq(reqId)
        return True

"""
    If only 1 user in the db have the provided value if the field for the provided key, this will return with that users' info.
"""
def getUser(key, value):
    # Ensure sql security.
    if not validate_sql(key) or not validate_sql(value):
        return {
            'return': False,
            'details': "Failed sql validation"
        }

    # Get lines from db.
    lines = to_sql('SELECT * FROM users WHERE "' + str(key) + '" = "' + str(value) + '"', 'r', "whm.db")['details']

    # Return user info if sql returned exactly 1 line.
    if len(lines) == 1:
        return {
            'return': True,
            'user': lines[0]
        }
    else:
        return {
            'return': False,
            'details': "SQL didn't return exactly 1 line"
        }

"""
    Returns all users their info from the users table by default.
    Can alternatively provide info from another table such as requests.
    *** group is placed into an sql command. Make sure it is safe before calling this.
"""
def getUsers(group="users"):
    # Get raw db lines.
    data = to_sql("SELECT * FROM " + group, "r", "whm.db")['details']
    # result will be build from data with any necessary processing.
    result = []
    # Mark all requesters as non-admins.
    if group == "requests":
        for request in data:
            result.append(request + (0,))
    else:
        result = data
    return result

# Run main once all functions are loaded.
if __name__ == "__main__":
    main()
