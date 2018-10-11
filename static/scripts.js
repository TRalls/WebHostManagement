/*
    This file is part of WHM front end documents. All webpages load this file from layout.html.
*/

// Metrics report is stored globally.
var report;

/*
    Declared in layout.html:
    var admin = '{{ session.admin }}';
    var user_id = '{{ session.user_id }}';
*/

// Onces front end files are loaded, route handing based on log in status.
$(document).ready(function() {
    if (user_id) {
        logged_in();
    } else {
        sessionStorage.clear();     // ensure empty session storage (report is stored here)
        not_logged_in();
    }
});

/*
    Actions to carry out if user is logged in.
*/
function logged_in() {
    // Remember which page is loaded.
    var page = window.location.pathname.split("/").pop();
    if (!page) {
        page = "home";
    }

    // If browser is not storing metrics report, load it.
    if (!sessionStorage.getItem('report')) {
        getReport();
    }

    // Load report from session storage. If not available yet, a temp report is created.
    report = JSON.parse(sessionStorage.getItem('report'));
    if (!report) {
        report = {
            status: "Loading...",
            demo: false
        };
    }

    // Handler to pull a new report.
    $('#refresh').click(function() {
        getReport();
    });

    // Show demo banner if demo mode is detected.
    if (report.demo) {
        $('#demo_banner').slideDown();
    }

    // Route execution based on the loaded page.
    switch (page) {
        case 'home':
            home();
            break;
        case 'settings':
            settings();
            break;
        case 'logs':
            logs();
            break;
        case 'processes':
            processes();
            break;
        case 'storage':
            storage();
            break;
        case 'network':
            $('div#network pre samp').html(report.network);
            break;
        case 'cpu':
            cpu();
            break;
        case 'memory':
            memory();
            break;
        case 'sensors':
            sensors();
            break;
    }

    // Show admin interface if admin is detected.
    if (admin == 1) {
        $("#username").css("color", "red");
        $('.admin').show();
    }
}

/*
    Actions to carry out if user is not logged in.
*/
function not_logged_in() {
    // Handler if login form submission.
    $('#login_form').on('submit', function(e) {
        e.preventDefault();         // prevent refresh - https://stackoverflow.com/questions/23507608/form-submission-without-page-refresh
        $.ajax({
            type: "POST",
            url: "login",
            data: $(this).serialize(),
            success: function(data){
                if (!data.success) {
                    // Handling succeeded, but log in failed.
                    alert("Failed to login:\n\n" + data.details);
                } else {
                    // User is logged in. Send them home.
                    document.location.href="/";
                }
            },
            error: function (jXHR, textStatus, errorThrown) {
                // Request failed.
                alert("Failed to verify credentials:\n\n" + errorThrown);
            }
        });
    });

    // Submission of user request form.
     $('#request_register_form').on('submit', function(e) {
        e.preventDefault();         // prevent refresh - https://stackoverflow.com/questions/23507608/form-submission-without-page-refresh
        // Local password check.
        if (this.password.value != this.vpassword.value) {
            alert("Passwords do not match.\nPlease try again.");
            return;
        }
        $.ajax({
            type: "POST",
            url: "register",
            data: $(this).serialize(),
            success: function(data){
                if (data.accepted) {
                    alert("Request Submitted:\n\n" +
                    "Once an admin approves your request, you will be able to log in with the details provided.\n" +
                    "Contact your admin for more details.");
                    document.location.href="/";
                } else {
                    alert("Request was not accepted:\n\n" + data.details);
                }
            },
            error: function (jXHR, textStatus, errorThrown) {
                alert("Failed to Submit:\n\n" + errorThrown);
            }
        });
    });
}

/*
    Home page route.
*/
function home() {
    // Add basic host details.
    $('#os').html(report.os);
    $('#hostname').html(report.hostname);
    $('#uptime').html(report.uptime);

    // Show demo mode details.
    if (report.demo) {
        $('#demo_desc').show();
    }

    // Hide standard user blurb if admin (admin blur will show when class is shown later if applicable).
    if (admin == 1) {
        $('#no_admin_desc').hide();
    }

    // Add full report to page and set up display toggling.
    $('#full_report').html(JSON.stringify(report, undefined, 2));
    $('#full_report_btn').click(function() {
        $('#full_report').toggle();
        if ($('#full_report_btn').html() == 'Show Raw Report') {
            $('#full_report_btn').html('Hide Raw Report');
            $('#full_report_btn').css({'background-color': '#bbbbbb'});
        } else {
            $('#full_report_btn').html('Show Raw Report');
            $('#full_report_btn').css({'background-color': '#eeeeee'});
        }
    });

    // Restart host handling.
    $('#restart_host').click(function() {
        if (confirm("You are about to reboot this host.\nAll services, including this webapp, will be interrupted.\nContinue?")) {
            $.ajax({
                type: 'POST',
                url: 'command',
                data: {
                    source: 'home',
                    action: 'restart'
                },
            });
            // There should be no return here. Assuming host is restarting.
            alert("Rebooting... Enjoy a random fact while system is rebooting.");
            //document.location.href="http://mentalfloss.com/amazingfactgenerator";
            window.open(
                'http://mentalfloss.com/amazingfactgenerator',
                '_blank'
            );
        }
    });
}

/*
    Sensors page route.
    Displays current and historical data.
*/
function sensors() {
    // For every device, display a bar chart with current metrics and a line chart for historical data.
    for (device in report.sensors) {
        table_and_chart(
            prefix = "sens_" + report.sensors[device].name0,
            title = report.sensors[device].name0 + " / " + report.sensors[device].name1,
            data = report.sensors[device].values,
            headers = ["Metric", "Value"],
            current_labels = null,
            default_unchecked = [],
            target_container = "sensors_charts",
            current_type = "bar"
        );
    }
}

/*
    Memory page route.
    Displays current and historical data.
*/
function memory() {
    // For each memory type, display a doughnut chart with current metrics and a line chart for historical data.
    for (group in report.memory) {
        table_and_chart(
            prefix = "mem_" + group,
            title = group + " Readings",
            data = report.memory[group],
            headers = ["Metric", "Value"],
            current_labels = ['used', 'free'],
            default_unchecked = ['total', 'free', 'utilization'],
            target_container = "memory_charts",
            current_type = "doughnut"
        );
    }

}

/*
    Storage page route.
*/
function storage() {
    // Build physical drive html
    for (var drive in report.drives) {
        var drive_html = '' +
        '<h3 class= "drive_name">' + drive + '</h3>' +
        '<div class="drive_details_container">' +
            '<div class="drive_left">' +
                '<h4>Details</h4>' +
                '<table>' +
                    '<tr>' +
                        '<td>Serial Number</td>' +
                        '<td>' + report.drives[drive].sn + '</td>' +
                    '</tr>' +
                    '<tr>' +
                        '<td>Smart Health</td>' +
                        '<td id="smart_health_' + drive + '">' + report.drives[drive].smart_health + '</td>' +
                    '</tr>' +
                    '<tr>' +
                        '<td>Size</td>' +
                        '<td>' + report.drives[drive].size + '</td>' +
                    '</tr>' +
                    '<tr>' +
                        '<td>Type</td>' +
                        '<td>' + report.drives[drive].type + '</td>' +
                    '</tr>' +
                '</table>' +
                '<h4>Partition Chart (GB)</h4>' +
                '<div class="partition_chart">' +
                    '<canvas id="partition_chart_' + drive + '" hight="400" width="400"></canvas>' +
                '</div>' +
            '</div>' +
            '<div class="drive_right">';

        // Build out partition html if partitions exist.
        if ('children' in report.drives[drive]) {
            drive_html += '<h4>Partitions</h4>' +
                get_part_html(report.drives[drive].children);
        }

        drive_html += '' +
            '</div>' +
        '</div>' +
        '<div class="smart_containter">' +
        '<h4>SMART Values</h4>' +
            '<span class="toggle">Expand Section</span>' +
            '<table class="smart_table">' +
                '<tr>';
        for (var header in report.drives[drive].smart_attributes[0]) {
            drive_html += '<th>' + header + '</th>';
        }
        drive_html += '</tr>';
        for (var attr in report.drives[drive].smart_attributes) {
            drive_html += '<tr>';
            for (header in report.drives[drive].smart_attributes[attr]) {
                drive_html += '<td>' + report.drives[drive].smart_attributes[attr][header] + '</td>';
            }
            drive_html += '</tr>';
        }
        drive_html += '</table></div>';
        $('#physical_drives').append(drive_html);

        // Style SMART health.
        if (report.drives[drive].smart_health == 'PASSED') {
            $('#smart_health_' + drive).addClass('smart_pass');
        } else {
            $('#smart_health_' + drive).addClass('smart_fail');
        }

        // Initialize chart info.
        var chart_data = {
            partitions: [],
            data: []
        };

        // Used to convert unit leters to gigabyte values.
        var unit_size = {
            K: (1/1024/1024),
            M: (1/1024),
            G: 1,
            T: 1024,
        };

        // Build chart_data and draw chart.
        for (var partition in report.drives[drive].children) {
            chart_data.partitions.push(partition);
            var size_str = report.drives[drive].children[partition].size;
            chart_data.data.push(parseFloat(size_str.slice(0, -1)) * unit_size[size_str.slice(-1)]);
        }
        draw('partition_chart_' + drive, 'doughnut', chart_data, 'partitions', null);
    }

    // Builds list of partition/children and is used recursively if a child has children.
    function get_part_html(parts) {
        var html = '<ul>';
        for (var part in parts) {
            html += '<li class="partitions">' + part + '</li><li class="partitions_details"><ul class="' + part + '_ul">';
            for (var key in parts[part]) {
                if (key != 'children') {
                    html += '<li class="partitions_details">' + key + ' : ' + parts[part][key] + '</li>';
                }
            }
            if ('children' in parts[part]) {
                html += get_part_html(parts[part].children);
            }
            html += '</ul></li>';
        }
        html += '</ul>';
        return html;
    }


    // Set up html for logical storage.
    var more_ld_mounts = [];
    var ld_html = '';
    // Build html for each logical volume that starts with /dev/, remember the ones that don't to build later.
    for (var ld in report.logical_volumes) {
        if (report.logical_volumes[ld].filesystem.substring(0, 5) == '/dev/') {
            var ld_name = report.logical_volumes[ld].filesystem.slice(5);
            ld_html += get_ld_html(report.logical_volumes[ld]);
            $('.' + ld_name + '_ul').append('<li class="partitions_details"><a href="#' + ld_name + '_h">Logical Drive Info</a></li>');
        } else {
            more_ld_mounts.push(report.logical_volumes[ld].mount_point.replace(/\//g, '_'));
        }
    }

    // Build html for logical volumes not starting with /dev/. These can be viewed by clicked an Expand button.
    if (more_ld_mounts.length > 0) {
        ld_html += '' +
            '<h4>More Logical Volumes:</h4>' +
            '<span class="toggle">Expand Section</span>' +
            '<div id="more_ld">';
        for (var ld in report.logical_volumes) {
            if (report.logical_volumes[ld].filesystem.substring(0, 5) != '/dev/') {
                ld_html += get_ld_html(report.logical_volumes[ld]);
            }
        }
        ld_html += '</div>';
    }

    // div for logical volume utilization record chart.
    ld_html += '<div id="ld_hist"></div>';

    // Add html to page.
    $('#logical_drives').html(ld_html);

    // Draw each logical volume utilization chart.
    for (var ld in report.logical_volumes) {
        draw(
            'ld_chart_' + report.logical_volumes[ld].mount_point.replace(/\//g, "_"),
            'doughnut',
            {
                data: [report.logical_volumes[ld].used, report.logical_volumes[ld].available],
                labels: ['Used', 'Free']
            },
            'labels',
            null
        );
    }

    // Chart historical utilization.
    table_and_chart(
        prefix = "sto",
        title = "Utilization History",
        data = {},
        headers = [],
        current_labels = [],
        default_unchecked = more_ld_mounts,
        target_container = "ld_hist",
        current_type = "doughnut"
    );

    // This is a unique case of table_and_chart usage. Remove or hide elements that are not applicable here.
    $('#ld_hist div .chart_sub_headers').remove();
    $('#ld_hist div .current_table_div').remove();
    $('#ld_hist div .current_chart_cont').css('display', 'none');

    // Build html for a logical drive.
    function get_ld_html(ld) {
        var html;
        // filesystem names starting with /dev/ are marked with id attr for <a> targets.
        if (ld.filesystem.substring(0, 5) == '/dev/') {
            html = '<h3 id="' + ld.filesystem.slice(5) + '_h" class="drive_name">' + ld.filesystem + '</h3>';
        } else {
            html = '<h3 class="drive_name">' + ld.filesystem + '</h3>';
        }
        html += '' +
            '<div class="drive_details_container">' +
                '<div class="drive_left">' +
                    '<h4>Details</h4>' +
                    '<table>' +
                        '<tr>' +
                            '<td>Mount Point</td>' +
                            '<td>' + ld.mount_point + '</td>' +
                        '</tr>' +
                        '<tr>' +
                            '<td>Size</td>' +
                            '<td>' + (ld.k_blocks/1024/1024).toFixed(2) + 'G</td>' +
                        '</tr>' +
                        '<tr>' +
                            '<td>Space Used</td>' +
                            '<td>' + (ld.used/1024/1024).toFixed(2) + 'G</td>' +
                        '</tr>' +
                            '<td>Percent Used</td>' +
                            '<td>' + ld.use_percent + '</td>' +
                        '</tr>' +
                    '</table>' +
                '</div>' +
                '<div class="drive_right">' +
                    '<div class="partition_chart">' +
                        '<canvas id="ld_chart_' + ld.mount_point.replace(/\//g, "_") + '" hight="400" width="400"></canvas>' +
                    '</div>' +
                '</div>' +
            '</div>';

        return html;
    }

    // Handler for toggle button. Toggest the element directly following the button.
    $('.toggle').click(function() {
        $(this).next().toggle();
        if ($(this).html() == 'Expand Section') {
            $(this).html('Collapse Section');
            $(this).css({'background-color': '#bbbbbb'});
        } else {
            $(this).html('Expand Section');
            $(this).css({'background-color': '#eeeeee'});
        }
    });
}

/*
    CPU page route.
    Displays current and historical data.
*/
function cpu() {
    // Display a doughnut chart with current metrics and a line chart for historical data.
    table_and_chart(
        prefix = "cpu",
        title = "CPU Readings",
        data = report.cpu,
        headers = ["Task", "Utilization"],
        current_labels = null,
        default_unchecked = ['idle'],
        target_container = "cpu_charts",
        current_type = "doughnut"
    );

}

/*
    Processes page route.
    Add running processes to the html table and give admins access to process actions.
*/
function processes() {
    // This is hold the html to add to the table.
    var rows_html = "";

    // Order of table headers.
    var ordered_keys = ['pid', 'tty', 'time', 'cmd'];

    // For each process, start a new table row and add process details as table data.
    for (line in report.processes) {
        rows_html += "<tr>";
        for (column in ordered_keys) {
            rows_html += "<td>" + report.processes[line][ordered_keys[column]] + "</td>";

        }

        // Add action buttons viewable by admins only, then end the row. Buttons are identifiable by pid.
        rows_html += "<td class='admin'>" +
            "<button id='hang-pid-" + report.processes[line]['pid'] + "' class='btn btn-default process-btn'>Hang Up (soft)</button>" +
            "<button id='kill-pid-" + report.processes[line]['pid'] + "' class='btn btn-default process-btn'>Kill (hard)</button>" +
        "</td>";
        rows_html += "</tr>";
    }

    // Add new html to the table.
    $('#processes_table').append(rows_html);

    // Handler for process buttons. Handling will be blocked at server if not an admin.
    $('.process-btn').click(function() {
        $.ajax({
            type: 'POST',
            url: 'command',
            data: {
                source: 'processes',
                action: $(this).attr('id').substring(0, 4),
                pid: $(this).attr('id').substring(9)
            },
            success: function(data) {
                // Notify results and get new report.
                alert(data.details);
                getReport();
            }
        });
    });
}

/*
    Logs page route.
*/
function logs() {
    // Display host logs and scroll to the latest entries.
    $('#dmesg_logs pre samp').html(report.dmesg);
    $('#dmesg_logs pre').scrollTop($('#dmesg_logs pre')[0].scrollHeight);

    // If user is an admin, show user logs.
    if (admin == 1) {
        get_logs('whm.log');

        // Listen for selection of archived log - display if selected.
        $('#lognames_btn').click(function() {
            get_logs($('#lognames').val());
        });
    }
}

/*
    Settings page route.
*/
function settings() {
    // Clear form data.
    $('#update_info')[0].reset();
    $('#update_other_info')[0].reset();
    $('#set_log_config')[0].reset();
    $('#set_record_config')[0].reset();
    $('#set_port_config')[0].reset();
    $('#record_default_flag').val(0);
    $('#port_default_flag').val(0);
    $('#default_flag').val(0);

    // This block is only applicable to admins
    if (admin == 1) {
        // Adjust UI for admin.
        $('td#priv').html('Admin');
        $('td#priv').css('color', 'red');

        // Indexes from db that should be included in html tables (excluded user_id and pw info).
        var indexes = [1, 3, 4, 5, 6];

        // Pull requests from db, add requests to page, and set up related handlers.
        $.ajax({
            type: 'POST',
            url: 'settings',
            data: {
                'action': 'get_table',
                'table': 'requests'
            },
            success: function(data) {
                // Build html from data and add it to the table.
                var html = "";
                if (data.lines.length > 0) {
                    for (var user in data.lines) {
                        html += "<tr>";
                        // For each index besides user_id and password hash.
                        for (var i in indexes) {
                            html += "<td>" + data.lines[user][indexes[i]] + "</td>";
                        }
                        html += "<td id='" + data.lines[user][0] + "'>";
                        html += "<select class='form-control' name='action'>" +
                                    "<option value='none'>- Select Action -</option>" +
                                    "<option value='decline'>Decline</option>" +
                                    "<option value='accept'>Accept</option>" +
                                "</select>" +
                                "<button class='btn btn-default requests_go'>Go</button>";
                        html += "</td>";
                        html += "</tr>";
                    }
                    $('#requests_table').append(html);
                } else {
                    // There was no data in db table.
                    $("#requests_table").replaceWith("<p><i>There are no pending requests.</i></p>");
                }

                // Handler request table actions by sending the context of the clicked button to the server.
                $('.requests_go').click(function() {
                    if ($(this).prev().val() != "none") {
                        $.ajax({
                            type: 'POST',
                            url: 'settings',
                            data: {
                                'table': 'requests',
                                'request_id': $(this).parent().attr('id'),
                                'action': $(this).prev().val()
                            },
                            success: function(data) {
                                if (!data.return) {
                                    alert("There was an error accepting the request.\n\n" +
                                    "This may occur if the requested username is already being used\n" +
                                    "It is recommended to decline this request and notify the requester to resubmit.");
                                }
                                location.reload();
                            }
                        });
                    }
                });
            }
        });

        // Pull current users from db, add users to page, and set up related handlers.
        $.ajax({
            type: 'POST',
            url: 'settings',
            data: {
                'action': 'get_table',
                'table': 'users'
            },
            success: function(data) {
                // Set up html based on data and add it to the users table.
                var html = "";
                for (var user in data.lines) {
                    // Start new row. Current user has a different bg color.
                    if (data.lines[user][0] == user_id) {
                        html += "<tr style='background-color: #fbfbdb;'>";
                    } else {
                        html += "<tr>";
                    }
                    // Add data to cells.
                    for (var i in indexes) {
                        html += "<td>" + data.lines[user][indexes[i]] + "</td>";
                    }
                    // Convert admin flag from 1/0 to YES/NO.
                    if (data.lines[user][7] == 1) {
                        html += "<td>YES</td>";
                    } else {
                        html += "<td>NO</td>";
                    }
                    // If not the current user, actions.
                    if (data.lines[user][0] == user_id) {
                        html += "<td></td>";
                    } else {
                        html += "<td id='data_i_" + user + "'>";
                        html += "<select class='form-control' name='action'>" +
                                    "<option value='none'>- Select Action -</option>" +
                                    "<option value='delete'>Delete</option>" +
                                    "<option value='toggle'>Toggle Admin</option>" +
                                    "<option value='update'>Update Info...</option>" +
                                "</select>" +
                                "<button class='btn btn-default users_go'>Go</button>";
                        html += "</td>";
                    }
                    html += "</tr>";
                }
                $('#users_table').append(html);

                // Users tables action handler.
                $('.users_go').click(function() {
                    // Send request to server based on the context of the clicked button if the action is not "update".
                    if ($(this).prev().val() != "none" && $(this).prev().val() != "update") {
                        $.ajax({
                            type: 'POST',
                            url: 'settings',
                            data: {
                                'table': 'users',
                                'request_id': data.lines[$(this).parent().attr('id').slice(7)][0],
                                'action': $(this).prev().val()
                            },
                            success: function(data) {
                                location.reload();
                            }
                        });
                    // Handler for update action.
                    } else if ($(this).prev().val() == "update") {
                        // Show div with a form related to the selected user and ensure fields are empty and submit handler is off.
                        $('#update_other_info')[0].reset();
                        $('#update_other_info').off();
                        $('#update-other-user').show();

                        // Display current user info on this div and go to this section of the page.
                        user_info = data.lines[$(this).parent().attr('id').slice(7)];
                        $('#other_username').html(user_info[1]);
                        if (user_info[7] == 1) {
                            $('#other_priv').html('Admin');
                            $('#other_priv').css('color', 'red');
                        } else {
                            $('#other_priv').html("Standard");
                            $('#other_priv').css('color', 'black');
                        }
                        $('#other_first').html(user_info[3]);
                        $('#other_last').html(user_info[4]);
                        $('#other_email').html(user_info[5]);
                        $('#other_phone').html(user_info[6]);
                        document.location.href="#update-other-user";

                        // Listener for the form on this new div.
                        $('#update_other_info').on('submit', function(e) {
                            e.preventDefault();         // prevent refresh - https://stackoverflow.com/questions/23507608/form-submission-without-page-refresh

                            // Ensure data was entered and validate passwords if entered.
                            if (this.npassword.value || this.vpassword.value) {
                                if (this.npassword.value && this.vpassword.value) {
                                    if (this.npassword.value != this.vpassword.value) {
                                        alert("Passwords are not the same.");
                                        return;
                                    }
                                } else {
                                    alert("If you need to change the password, please enter both password fields.");
                                    return;
                                }
                            } else if (!(this.first.value || this.last.value || this.email.value || this.phone.value)) {
                                alert("No data was entered.");
                                return;
                            }

                            // Send update to server.
                            $.ajax({
                                type: "POST",
                                url: "settings",
                                data: $(this).serialize() + '&user_id=' + user_info[0],
                                success: function(data){
                                    if (data.return) {
                                        alert(data.details);
                                        location.reload();
                                    } else {
                                        alert("Request was not accepted:\n\n" + data.details);
                                    }
                                },
                                error: function (jXHR, textStatus, errorThrown) {
                                    alert("Failed to Submit:\n\n" + errorThrown);
                                }
                            });

                        });

                        // Handler to close user edit div.
                        $('#close-other-user').click(function() {
                            $('#update-other-user').hide();
                            document.location.href="#admin-settings";
                        });
                    }
                });
            }
        });

        // Load config and update content on page.
        $.ajax({
            type: 'POST',
            url: 'settings',
            data: {
                'action': 'get_config'
            },
            success: function(data) {
                if (!data.return) {
                    alert(data.details);
                    $('#max_size_value').html("Failed to Load.");
                    $('#max_age_value').html("Failed to Load.");
                    $('#usr_len_value').html("Failed to Load.");
                    $('#src_len_value').html("Failed to Load.");
                    $('#record_hours_value').html("Failed to Load.");
                    $('#record_days_value').html("Failed to Load.");
                    $('#record_weeks_value').html("Failed to Load.");
                    $('#port_n').html("Failed to Load.");
                } else {
                    $('#max_size_value').html(data.max_log_size);
                    $('#max_age_value').html(data.max_log_age_n + " " + data.max_log_age_unit.slice(0, -1) + "(s)");
                    $('#usr_len_value').html(data.user_str_len);
                    $('#src_len_value').html(data.source_str_len);
                    $('#max_age_unit').val(data.max_log_age_unit);
                    $('#record_hours_value').html(data.hours_age_max);
                    $('#record_days_value').html(data.days_age_max);
                    $('#record_weeks_value').html(data.weeks_age_max);
                    $('#port_n').html(data.port_n);
                }
            }
        });

        // Handler for changing config settings.
        $('.set_config').on('submit', function(e) {
            e.preventDefault();         // prevent refresh - https://stackoverflow.com/questions/23507608/form-submission-without-page-refresh
            $.ajax({
                type: "POST",
                url: "settings",
                data: $(this).serialize() + '&action=set_config',
                success: function(data){
                    if (data.return) {
                        location.reload();
                    } else {
                        alert("Request was not accepted:\n\n" + data.details);
                    }
                },
                error: function (jXHR, textStatus, errorThrown) {
                    alert("Failed to Submit:\n\n" + errorThrown);
                }
            });
        });

        // Default config handlers. 1 signifies default button was clicked.
        $('#logs_to_default').click(function() {
            $('#log_default_flag').val(1);
            $('#set_log_config').submit();
        });
        $('#record_to_default').click(function() {
            $('#record_default_flag').val(1);
            $('#set_record_config').submit();
        });
        $('#port_to_default').click(function() {
            $('#port_default_flag').val(1);
            $('#set_port_config').submit();
        });
    }

    // End of admin block. The below code runs for all users.

    // Update account info handler.
    $('#update_info').on('submit', function(e) {
        e.preventDefault();         // prevent refresh - https://stackoverflow.com/questions/23507608/form-submission-without-page-refresh

        // Ensure data is entered and validate passwords.
        if (this.password.value || this.npassword.value || this.vpassword.value) {
            if (this.password.value && this.npassword.value && this.vpassword.value) {
                // All password fields were entered.
                if (this.npassword.value != this.vpassword.value) {
                    alert("New passwords don't match.");
                    return;
                }
            } else {
                // Password fields had values, but not all of them.
                alert("If you would like to change your password, please fill out all of the password fields.\n" +
                    "Otherwise, leave them all blank.\n\nNo updates were sent.");
                return;
            }
        } else {
            if (!(this.first.value || this.last.value || this.email.value || this.phone.value)) {
                // No values entered
                alert("No data was entered.");
                return;
            }
        }

        // Send update to server.
        $.ajax({
            type: "POST",
            url: "settings",
            data: $(this).serialize(),
            success: function(data){
                if (data.return) {
                    alert(data.details);
                    location.reload();
                } else {
                    alert("Request was not accepted:\n\n" + data.details);
                }
            },
            error: function (jXHR, textStatus, errorThrown) {
                alert("Failed to Submit:\n\n" + errorThrown);
            }
        });
    });
}

/*
    Request user logs from the server and display them on the page.
    Server will block requests from non-admins.
*/
function get_logs(logname) {
    $.ajax({
        type: 'GET',
        url: 'logs',
        data: {
            'action': 'get_whm_logs',
            'logname': logname
        },
        success: function(data) {
            // Ensure propper return of logs.
            if (data.return == 'Failed to read logs...') {
                alert(data.return);
            }

            // Display log data, and scroll to the latest evets.
            $('#whm_logs pre samp').html(data.return.log_text);
            $('#whm_logs pre').scrollTop($('#whm_logs pre')[0].scrollHeight);

            // Load available archived logs as select options.
            var log_files_html = "";
            for (file in data.return.log_files) {
                log_files_html += "<option>" + data.return.log_files[file] + "</option>";
            }
            $('#lognames').html(log_files_html);

            // Update div header info.
            $('#logname').html(logname);
            $('#lognames').val(logname);
        }
    });
}

/*
    Pull current metrics from the server.
    Store the data in session storage and refresh the page.
*/
function getReport() {
    // Limit interface while report is loading.
    $('.navbar-right').html('');
    $('.navbar-left').html('');
    $('.navbar-brand').attr('href', '#');
    $('main').html('' +
        '<div class="boxed-div">' +
            '<h1>Loading Metrics</h1>' +
            '<p>Please wait...<p>' +
        '</div>'
    );

    // Pull report.
    $.ajax({
        type: 'GET',
        url: 'getReport',
        success: function(data) {
            sessionStorage.setItem("report", JSON.stringify(data["report"]));
            location.reload();
        },
        error: function (jXHR, textStatus, errorThrown) {
            alert("Failed to get report...:\n\n" + errorThrown);
        }
    });
}

/*
    Inplements chart.js to graphically display current and historical metrics.
    Provide the following:
        canvas_id: String. The target canvas id for the chart to be displayed in.
        type: String. Type of chart to use. Bar and doughnut are intended for current metrics, and line is intended for historical data.
        data: Object containing lists of data points and labels indexed in order. For example there could be a list of X values and a list of Y values.
        labels_key: String. The key in the object that will be used as labels or as the X-axes.
        oldchart: chart Obj that may need to be cleared before drawing a new chart.
*/
function draw(canvas_id, type, data, labels_key, oldchart) {
    // List of colors that may be used to identify data.
    var colors = ["#dbdb7b", "#db7b7b", "#7b7b7b", "#7bdb7b", "#7bdbdb", "#7b7bdb", "#db7bdb", "#abdbab", "#abdbdb"];

    // Initialize datasets and options for Chart.
    var datasets = [];
    var options = {};

    // Line charts are used for historical data and use time as the label.
    if (type == "line") {
        for (key in data) {
            // Skip processing of time data.
            if (key == "time") {
                continue;
            }
            // Add each non-label list in data to dataset
            datasets.push({
                data: data[key] ,
                label: key,
                borderColor: colors.pop(),
                backgroundColor: "#dbdbdb",
                fill: false
            });
        }

        // Clear old chart if needed.
        if (oldchart!=null) {
            oldchart.destroy();
        }

        // Set table options to properly fomat the X-Axes for time.
        options = {
            scales: {
                xAxes: [{
                    type: "time",
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'DD'
                        }
                    }
                }, {
                    type: "time",
                    time: {
                        unit: 'month',
                        round: 'month',
                        displayFormats: {
                            month: 'MMMYY'
                        }
                    }
                }]
            }
        };

    // This is for current metrics. Chart can take data as is.
    } else {
        datasets.push({
            data: data.data,
            backgroundColor: colors
        });
    }

    // These bar charts deliver a clear message without legen labels due to surrounding elements.
    if (type == "bar") {
        options.legend = {
            display: false
        };
    }

    // Create chart in the specified canvas using datasets and options as built above.
    var chart = new Chart($('#' + canvas_id)[0].getContext('2d'), {
        type: type,
        data: {
            labels: data[labels_key],
            datasets: datasets
        },
        options: options
    });

    // Return chart so it can be kept and cleared later if needed.
    return chart;
}

/*
    All in one drawing and event handling for current metrics table, current metrics chart, and historical metrics chart.
    Each device with current and tracked metrics can use this function. CPU statisics for example. Or any specific sensor.
    Provide the following:
        prefix: String. The prefix for all elements related to this set of charts. "mem_Swap" for example.
            This is also how the data will be identified in the db. For examplet the above would pull data from table mem_Swap_xxxxx.
        title: String. Title for the top of the div.
        data: Obj. A set of data from report. The object should have keys identifying chartable data. The values of these keys should be numeric.
        headers: Array of Strings. Headers as displayed at the top of the current metrics table. These should be in key, vlaue order corresponding to data.
        current_labels: Array of Strings. Items from key_order that should be displayed on current data chart (pass null if same as key_order).
        default_unchecked: Array of Strings. Items from key_order that should be unchecked by default on historical data chart.
        target_container: String. Id of the div that this charts will be appended to.
        current_type: String. Type of chart to use to display current data. ex. "doughnut" or "bar"

    key_order no longer needs to be provided, but it is an array of Strings. Order of values as stored in the db minus time, which will always be first.
*/
function table_and_chart(prefix, title, data, headers, current_labels, default_unchecked, target_container, current_type) {
    // Build div for a new set of tables and charts and at it to target_container.
    var html = '<div class="boxed-div">' +
        '<h2 id="' + prefix + '_current_title" class="chart_title">' + title + '</h2>' +
        '<h4 class="chart_sub_headers">Current:</h4>' +
        '<div class="boxed-box current_chart_cont">' +
            '<canvas id="' + prefix + '_current_chart" hight="400" width="400"></canvas>' +
        '</div>' +
        '<div class="boxed-box current_table_div">' +
            '<table id="' + prefix + '_current_table" class="current_table">' +
            '<tr>';
                for (i in headers) {
                    html += '<th>' + headers[i] + '</th>';
                }
            html += '</tr>' +
            // Table headers are done, data will be added later.
            '</table>' +
        '</div>' +

        '<h4 class="chart_sub_headers">Historic:</h4>' +
        // Historic data control section.
        '<div class="chart_info">' +
            '<form id="' + prefix + '_chart_form" class="chart_form"></form>' +
            '<label>Scope: </label>' +
            '<select id="' + prefix + '_chart_scope" class="form-control">' +
                '<option value="hours" selected>Hours</option>' +
                '<option value="days">Days</option>' +
                '<option value="weeks">Weeks</option>' +
            '</select>' +
        '</div>' +
        '<canvas id="' + prefix + '_history_chart" width="400" height="400"></canvas>' +
        '<div class="chart_info" id="' + prefix + '_no_chart">' +
            '<i>No data at this scale is available yet. Check a smaller scale or check back later.</i>' +
        '</div>' +
    '</div>';
    $('#' + target_container).append(html);

    // Initialize current data.
    var processed_current_data = {
        labels: [],
        data: []
    };

    // Get key_order from DB.
    $.ajax({
        type: 'POST',
        url: 'chart_data',
        data: {
            data_set: prefix,
            scale: 'hours',
            data_needed: 'keys'
        },
        success: function(db_data) {

            var key_order = db_data.keys;

            // If current_labels is null, it is set to key_order.
            if (current_labels == null) {
                current_labels = key_order;
            }

            // For each key provided:
            for (var i = 0; i < key_order.length; i++) {
                // Add this key, value to current metrics table.
                $("#" + prefix + "_current_table").append("<tr><td>" + key_order[i] + "</td><td>" + data[key_order[i]] + "</td></tr>");

                // Add checkbox for this key on historic data chart control.
                var checkbox_html = "<div><input type='checkbox' name='" + key_order[i] + "' id='" + key_order[i] + "' ";
                if (!default_unchecked.includes(key_order[i])) {
                    checkbox_html += "checked ";
                }
                checkbox_html += "/><label>" + key_order[i] + "</label></div>";
                $('#' + prefix + '_chart_form').append(checkbox_html);

                // Add data to current data so it can be accepted by draw(). See the difference between how this
                // function accepts data and draw() accepts data.
                if (current_labels.includes(key_order[i])){
                    processed_current_data.labels.push(key_order[i]);
                    processed_current_data.data.push(data[key_order[i]]);
                }
            }

            // Draw current metrics chart.
            draw(prefix + '_current_chart', current_type, processed_current_data, 'labels', null);

            // Initialize a new chart var.
            var chart;

            // Anytime scope is changed. This refers to Hours, Days, and Weeks.
            $('#' + prefix + '_chart_scope').change(function() {

                // Reset chart form listener. Will be added back later if applicable.
                $('#' + prefix + '_chart_form').off('change');

                // Get historical data for this device/prefix at the specified scale.
                $.ajax({
                    type: 'POST',
                    url: 'chart_data',
                    data: {
                        data_set: prefix,
                        scale: this.value,
                        data_needed: 'history'
                    },
                    success: function(db_data) {
                        // If no data was returned, show no data message.
                        if (!db_data.success || db_data.data.length == 0) {
                            $('#' + prefix + '_history_chart').hide();
                            $('#' + prefix + '_no_chart').show();
                            return;
                        }

                        // Data returned. Set elements for data display.
                        $('#' + prefix + '_history_chart').show();
                        $('#' + prefix + '_no_chart').hide();

                        // When labels are checked/unchecked:
                        $('#' + prefix + '_chart_form').change(function() {
                            // Initialize historical data to process data into.
                            var processed_data = {
                                time: []
                            };

                            // Initialize a cache of keys/fields and their index in db_data.data.
                            var index_of_cache = {
                                time: 0
                            };

                            // For keys/fields that are checked, initialize their array in proccessed data and cache their db index.
                            for (var i = 0; i < key_order.length; i++) {
                                if ($('#' + prefix + '_chart_form input#' + key_order[i]).is(':checked')){
                                    processed_data[key_order[i]] = [];
                                    index_of_cache[key_order[i]] = i + 1;
                                }
                            }

                            // Convert db_data to processed_data.
                            for (var i = 0; i < db_data.data.length; i++) {
                                for (key in processed_data) {
                                    processed_data[key].push(db_data.data[i][index_of_cache[key]]);
                                }
                            }

                            // Draw historical metrics chart.
                            chart = draw(prefix + '_history_chart', 'line', processed_data, 'time', chart);
                        });

                        // Run field/key change handler to set up chart on ajax return.
                        $('#' + prefix + '_chart_form').trigger('change');
                    }
                });
            });

            // Run scope change handler to pull ajax on page load.
            $('#' + prefix + '_chart_scope').trigger('change');
        }
    });
}
