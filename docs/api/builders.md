# Builders API

Fluent builders for creating systemd unit files. Each builder follows a
chain-style API: call methods to set directives, then `.build()` to
validate and render a `UnitFile`.

## ServiceBuilder

::: systemd_client.builders.ServiceBuilder
    options:
      members:
        - __init__
        - description
        - after
        - before
        - requires
        - wants
        - type_
        - exec_start
        - exec_start_pre
        - exec_start_post
        - exec_stop
        - exec_reload
        - restart
        - restart_sec
        - watchdog_sec
        - user
        - group
        - working_directory
        - environment
        - environment_file
        - standard_output
        - standard_error
        - runtime_directory
        - state_directory
        - syslog_identifier
        - remain_after_exit
        - private_tmp
        - protect_system
        - protect_home
        - dynamic_user
        - nice
        - limit_nofile
        - wanted_by
        - required_by
        - also
        - build

## TimerBuilder

::: systemd_client.builders.TimerBuilder
    options:
      members:
        - __init__
        - description
        - after
        - wants
        - on_calendar
        - on_boot_sec
        - on_startup_sec
        - on_unit_active_sec
        - on_unit_inactive_sec
        - on_active_sec
        - persistent
        - accuracy_sec
        - randomized_delay_sec
        - unit
        - wanted_by
        - build

## SocketBuilder

::: systemd_client.builders.SocketBuilder
    options:
      members:
        - __init__
        - description
        - after
        - wants
        - listen_stream
        - listen_datagram
        - listen_sequential_packet
        - listen_fifo
        - accept
        - socket_user
        - socket_group
        - socket_mode
        - service
        - max_connections
        - keep_alive
        - wanted_by
        - build

## PathBuilder

::: systemd_client.builders.PathBuilder
    options:
      members:
        - __init__
        - description
        - after
        - wants
        - path_exists
        - path_exists_glob
        - path_changed
        - path_modified
        - directory_not_empty
        - unit
        - make_directory
        - trigger_limit_interval_sec
        - trigger_limit_burst
        - wanted_by
        - build
