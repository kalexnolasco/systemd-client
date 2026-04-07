# Notify API

Pure-Python implementation of the `sd_notify(3)` protocol. Send
lifecycle notifications to systemd from a `Type=notify` service
without any C dependencies.

## SystemdNotifier

::: systemd_client.notify.SystemdNotifier
    options:
      members:
        - __init__
        - available
        - notify
        - ready
        - status
        - stopping
        - reloading
        - watchdog
        - errno
        - mainpid
        - extend_timeout
        - close
