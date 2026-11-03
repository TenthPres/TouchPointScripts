# Pckgd
# Title: Atrium Control
# Description: Wireless lock battery report, plus code-callable momentary unlock and lockdown start/stop.
# Updates from: GitHub/TenthPres/TouchPointScripts/AtriumControl/AtriumControl.py
# Depends on: AtriumLib.py
# Version: 0.1.0
# License: AGPL-3.0
# Author: James at Tenth
# Editable: False

# Do not make edits to this file.  They will be overwritten during updates.

# Open /PyScript/AtriumControl for the battery report.
#
# From another TouchPoint script:
#
#     Data.AtriumAction = "unlock"            # or "lockdown_start" / "lockdown_stop"
#     Data.AtriumDoor = "Front Doors"         # a name from AtriumConfig.json -> "doors" (unlock only)
#     Data.AtriumSeconds = 30                 # optional; defaults to 15
#     Data.AtriumConfirm = "YES"              # required; nothing happens without it
#     model.CallScript("AtriumControl")
#
# AtriumConfig.json -> "doors" maps friendly names to controllers:  {"Front Doors": {"serial": "00009F90", "id": 0}}
# Lockdown is not tied to any door: it applies to the whole system.  Every action is printed to the script output.

global model, Data, q

import json

try:
    exec(model.PythonContent("AtriumLib"), globals())
except NameError:  # running under test
    from AtriumLib import *  # noqa

DEFAULT_UNLOCK_SECONDS = 15


def client_from_settings():
    return AtriumClient(model.Setting("AtriumApiUrl", ""), model.Setting("AtriumApiUser", ""),
                        model.Setting("AtriumApiPassword", ""), touchpoint_transport(model))


def resolve_door(config, name):
    door = (config.get("doors") or {}).get(name)
    if door is None:
        raise AtriumError("No door named '{}' in AtriumConfig.json".format(name))
    return door["serial"], int(door["id"])


def battery_summary(locks):
    """(label, status) per lock, worst first.  Trouble flags are authoritative; volts are informational."""
    def rank(l):
        return 0 if (l["battery_critical"] or not l["online"] or l["rf_loss"]) else 1 if l["battery_low"] else 2

    out = []
    for l in sorted(locks, key=rank):
        if not l["online"]:
            status = "OFFLINE"
        elif l["battery_critical"]:
            status = "CRITICAL"
        elif l["battery_low"]:
            status = "LOW"
        elif l["rf_loss"]:
            status = "RF LOSS"
        else:
            status = "OK"
        out.append((l, status))
    return out


def run_action(client, action, config, door, seconds, confirm):
    if confirm != "YES":
        raise AtriumError("Atrium action refused: AtriumConfirm must be 'YES'")
    if action == "unlock":
        serial, door_id = resolve_door(config, door)
        client.momentary_unlock(serial, door_id, seconds, confirm=True)
        print("<p>Unlocked '{}' for {} seconds.</p>".format(door, seconds))
    elif action == "lockdown_start":
        client.start_lockdown(confirm=True)
        print("<p><b>Lockdown started.</b></p>")
    elif action == "lockdown_stop":
        client.stop_lockdown(confirm=True)
        print("<p>Lockdown stopped.</p>")
    else:
        raise AtriumError("Unknown Atrium action '{}'".format(action))


def render_batteries(client):
    model.Title = "Atrium Wireless Locks"
    model.Header = "Atrium Wireless Locks"
    rows = []
    for l, status in battery_summary(client.wireless_lock_status()):
        rows.append("<tr><td>{}</td><td>{} #{}</td><td>{}</td><td>{} V</td></tr>".format(
            status, l["label"] or "Lock", l["id"], l["serial"], l["volts"]))
    print("<table class='table table-striped'><thead><tr><th>Status</th><th>Lock</th><th>Controller</th>"
          "<th>Battery (approx.)</th></tr></thead><tbody>{}</tbody></table>".format("".join(rows)))
    print("<p><small>Status comes from the lock's own low/critical flags.  Voltage is shown for trend-watching only.</small></p>")


def run():
    client = client_from_settings()
    action = getattr(Data, "AtriumAction", None) if hasattr(Data, "AtriumAction") else None
    if action:
        config = json.loads(model.TextContent("AtriumConfig.json") or "{}")
        run_action(client, action, config, getattr(Data, "AtriumDoor", None),
                   int(getattr(Data, "AtriumSeconds", DEFAULT_UNLOCK_SECONDS) or DEFAULT_UNLOCK_SECONDS),
                   getattr(Data, "AtriumConfirm", None))
    else:
        render_batteries(client)


if "model" in globals() and hasattr(model, "TextContent"):
    run()
