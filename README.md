# WHM

Web Host Management - Makes standalone server management easy.

## Why

WHM is intended for to be ran on a single physical host where that host alone provides various needs of its owner(s), such as a media or web server. It provides the owner(s) a web interface to conveniently check and track the health of the host. This saves the hassle of needing to periodically ssh to the host and googling diagnostic commands to ensure the host is still healthy. This application can also carry out some simple tasks such as rebooting the host and manipulating running services. There is also user management and logging functionality to ensure accountability if the owner(s) choose to delegate these tasks.

This application also serves as a final class project and a representation of my current skill level and style. See Credits for more on this.

## Dependencies

* Python3.5 or higher
* Flask
* Flask-Session
* passlib
* apscheduler
* lm-sensors
* smartmontools

## Install

* Ensure all dependencies are available.
* Change directories to where you intend to run the application from.
* Download the project.
```
git clone https://github.com/TRalls/WebHostManagement.git
```
* Change directories to WebHostManagement.
* Run users.py to create the first user account.
* The default network port is 8080. If this needs to be changed, edit whm.cfg.
    * Ensure your network equipment and settings allow the configured port to pass traffic.
* Start application.py as root.
* The application is now accessible by IP/Domain Name:Port.
* Consider auto-running this application on boot.

### Auto-Running

The setup to run this application at boot will vary by system. In order to get full functionality this application much run as root. The following worked for my system at home running Debian 3.16.51-3.
* Install sudo if not already installed.
* Set up a startup script in your location of choice. I named mine start.sh within my whm directory.
* Place the following in the script:
	* Note: changing directories will ensure application.py can access neighboring files.
```
cd [full/path/to/directory/containing/application.py]
sudo nohup python [full/path/to/application.py]
```
* As root, run crontab -e.
```
crontab -e
```
* Append the following line.
```
@reboot [full/path/to/the/startup/script/you/created]
```
* Restart system and ensure application is running. If you can use the restart button in the webapp, you should have full functionality.

## Build Status

Running with no known errors on physical hardware on Python3.6.6.
Running with no known errors on Cloud9 dev environment on Python3.6.0 (Demo mode).

## Stack

* HTML/CSS
    * Bootstrap
* Javascript
    * jQuery
    * Ajax
    * chart.js
    * moment.js
* Python3
    * Flask
    * Jinja
* SQLite3

## Usage

### Web Interface

#### New Users

New users should request access by going to the registration link an filling out the form. Each request much be reviewed and accepted by an admin before the requesting user can log in. If accepted, information provided by the request will be used to register the user.

#### User Privilege

Users created after the first user will default to standard users. Admins can make other users admins (and take away admin rights) if needed. Standard users can view current metrics, view historical metrics, view host logs, and change their own personal info. Admins can do all actions permitted to standard users and can also view usage, logs, issue commands to the host OS, view requesting and current user info (except for passwords), approve or decline requesting users, manage current users, and can change configuration settings. While logged in, standard users will see their username in gray on the nav bar. Admin users will see their username in red.

#### Demo Mode

Demo mode is triggered if no physical sensors are detected as determined by lm-sensors. No physical sensors would imply that the application is running on a virtual or cloud based host. These hosts fall outside of the intended scope of this project. The assumed use case for these hosts is that the user is testing out (or developing) the application. Therefore, all functionality must be present even if it's not all applicable. When demo mode is triggered, the OS will run commands to output samples from text files instead of running actual diagnostic commands where these diagnostic commands would not be applicable. This way the output will be processed and displayed to users in the same way live diagnostic output would. Users will know that they are using demo mode when there is an orange banner at the top of the page while logged in.

#### Current Metrics

All current metrics are as of the time the complete metrics report was pulled. This report is pulled when a user first logs in and can be viewed at the bottom of the home page. The report can be navigated in an easy to read format via the links on the nav bar. To pull an updated report of metrics while logged in, click the refresh button on the nav bar.

#### Historical Metrics

After this application is started and the first user logs in, it will start periodically checking metrics on an hourly, daily, and weekly basis. Information that is useful to track over time is recorded and viewable by users on various tabs on the nav bar. Historical data is dropped once it reaches a certain age. This can be configured on the Settings tab.

#### Diagnostic Tabs

The web interface has the following tabs:
* Sensors
    * Shows current and historical data for all devices that report by lm-sensors.
    * See specific hardware documentation for interpreting data in this section.
* Memory
    * Shows current and historical utilization for memory.
* CPU
    * Shows current and historical utilization of the CPU.
* Storage
    * Shows break down of partitions and details of physical drives and current and historical utilization of logical volumes.
* Processes
    * Lists currently running processes and allows admins to take some action on them.
* Network
    * Shows some network info, but it is deliberately cut short for now due to security concerns.
* Logs
    * Shows host logs. Admins can see user logs - See next section.

#### User Logs

Admins can view user logs on the logs tab. These logs show activities carried out with this application. This holds users accountable for their actions and can also aid in troubleshooting issues with this application. Logs are backed up and cleared once they reach a certain size. Backed up logs are also deleted when they reach a certain age. These values are configurable on the Settings tab.

#### Settings

Standard users only see a form to update their personal information here. Admins see the same form but can also manage current and requesting users from here. This is also where admins can configure behavior of logs and records of metrics. Configuration settings are stored in whm.cfg, but it is best not to edit this manually (except for port_n which may need to be changed manually to initially access the web interface).

### Command Line Tools

The following files are used by the application and can also be ran from the command line.

#### metrics
```
./metrics.py
```
* This file will output all of the host metrics reported by WHM in raw JSON.
```
./metrics.py update
```
* Outputs only the host metrics that are tracked over time in JSON.

#### users
```
./users.py
```
Used to manage current and requesting users. Text menus are used to navigate the functionality of this file. This file must be ran to create the first admin user before the web interface can be used. After this first user is created, all other new users default to standard (non-admin) users.

## Content

Screenshots:
https://photos.app.goo.gl/4YxeLtWohaHEVpm8A

Video:
TBD

## Security

This application was developed with security in mind but I do not guarantee safe operations while using it. Please note the following.
* This application can run OS commands. The commands that can be ran are limited and are set by arguments sent by the client. The OS never runs directly from a client request. Instead, logic is used to route the request to the appropriate command.
* All data sent from the client is checked before injecting into SQL commands.
* The client controls the view of the webpage based on whether the user is an admin or not, but this doesn't stop a user from sending requests to the server for actions that require admin rights to view. In these cases, the server redundantly checks that client users have rights to access the requested functionality. A standard user requesting access to admin functions indicates that the user likely sent the request manually and should be taken as a red flag. These activities are blocked and logged.
* Although passwords are stored in the database in an encrypted state, they are sent from the client to the server in clear text. These clear text passwords may be found on the network or in volatile memory while password activities are occurring.

## Contribute

This project is in near completed state and should only require small touch ups. Since I am an aspiring developer, I do welcome all feedback. I cannot promise to implement feature requests, but any and all feedback would help greatly.

## Credits

* An unnamed development training program that I am applying for that prompted me to take CS50
* CS50 via edX prompted me to create this project. It is an introduction to CS taught from Harvard and available online for free.
    * https://courses.edx.org/courses/course-v1:HarvardX+CS50+X/course/
    * Some style is inspired by the Finance problem set while using Bootstrap documentation.
* Refresh button asset
    * https://www.iconfinder.com/icons/134221/arrow_refresh_reload_repeat_sync_update_icon
    * License Creative Commons
* Form submission handling: https://stackoverflow.com/questions/23507608/form-submission-without-page-refresh
* Random facts while waiting for system reboots: https://mentalfloss.com

## License

Please feel free to use, modify, and distribute for free so long as it's not sold or directly used for financial gain. If you do use this software in any way, please simply send an email to tralls@outlook.com letting me know you are using it. No further information is needed.
