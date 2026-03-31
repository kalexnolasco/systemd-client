# Client API

## AsyncSystemdClient

::: systemd_client.client.AsyncSystemdClient
    options:
      members:
        - __init__
        - list_units
        - status
        - start
        - stop
        - restart
        - reload
        - enable
        - disable
        - mask
        - unmask
        - is_active
        - is_enabled
        - is_failed
        - daemon_reload
        - journal
        - journal_follow

## SystemdClient

::: systemd_client.client.SystemdClient
    options:
      members:
        - __init__
        - list_units
        - status
        - start
        - stop
        - restart
        - reload
        - enable
        - disable
        - mask
        - unmask
        - is_active
        - is_enabled
        - is_failed
        - daemon_reload
        - journal
        - journal_follow
