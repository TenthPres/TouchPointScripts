# Pckgd
# Title: Room Atrium Integration
# Description: Sync TouchPoint room reservations to CDVI Atrium schedules
# Updates from: GitHub/TenthPres/TouchPointScripts/Calendar/RoomAtriumIntegration.py
# Author: James at Tenth

global model, Data, q

import datetime
import hashlib
import json
import xml.etree.ElementTree as ET

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

try:
    from cgi import escape as html_escape
except ImportError:
    from html import escape as html_escape

_existing_config = None
_atrium_client = None
_events_to_add = None
_events_to_remove = None
_change_limit = 200


def _safe_int(value, default_value=0):
    try:
        return int(value)
    except Exception:
        return default_value


def _normalize_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _ascii_text(value, fallback="Reservation"):
    text = _normalize_text(value)
    if text == "":
        text = fallback
    text = "".join([c for c in text if ord(c) < 128])
    return text or fallback


def get_config():
    """Retrieves the shared room device configuration."""

    global _existing_config

    if _existing_config is None:
        _existing_config = model.TextContent("RoomDeviceConfiguration.json") or "{}"
        _existing_config = json.loads(_existing_config)

    return _existing_config


def save_config(config):
    model.WriteContentText("RoomDeviceConfiguration.json", json.dumps(config, indent=4))


def get_reservables(typ):
    """Retrieves reservables of the given type."""

    return q.QuerySql(
        """
        SELECT ReservableId,
               ParentId,
               Name,
               Description,
               IsReservable,
               IsEnabled
        FROM Reservable
        WHERE ReservableTypeId = {}
          AND IsDeleted = 0
          AND IsEnabled = 1
        ORDER BY Name;
        """.format(typ)
    )


class AtriumClient(object):
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password

        self.session_id = None
        self.session_key = None
        self.serial = None
        self.timeout_at = None

    @staticmethod
    def rc4(key, text):
        s = list(range(256))
        j = 0
        for i in range(256):
            j = (j + s[i] + ord(key[i % len(key)])) % 256
            s[i], s[j] = s[j], s[i]

        i = 0
        j = 0
        encrypted = ""
        for y in range(len(text)):
            i = (i + 1) % 256
            j = (j + s[i]) % 256
            s[i], s[j] = s[j], s[i]
            encrypted += "{:02X}".format(ord(text[y]) ^ s[(s[i] + s[j]) % 256])
        return encrypted


    @staticmethod
    def rc4_decrypt_hex(key, hex_text):
        """
        Decrypts a hex-encoded RC4 ciphertext (e.g. '4FA01B...') into plaintext.

        This is the inverse of rc4(key, plaintext) which returns hex.
        """
        # Defensive: strip whitespace/newlines if present
        hex_text = "".join(hex_text.split())

        # Must be even length hex
        if len(hex_text) % 2 != 0:
            raise ValueError("RC4 hex ciphertext length must be even")

        # Convert hex pairs to byte values (0-255)
        cipher_bytes = [int(hex_text[i:i+2], 16) for i in range(0, len(hex_text), 2)]

        # RC4 KSA
        s = list(range(256))
        j = 0
        for i in range(256):
            j = (j + s[i] + ord(key[i % len(key)])) % 256
            s[i], s[j] = s[j], s[i]

        # RC4 PRGA
        i = 0
        j = 0
        out_chars = []
        for cb in cipher_bytes:
            i = (i + 1) % 256
            j = (j + s[i]) % 256
            s[i], s[j] = s[j], s[i]
            k = s[(s[i] + s[j]) % 256]
            out_chars.append(chr(cb ^ k))

        return "".join(out_chars)


    @staticmethod
    def decrypt_xml(self, xml_data):
        """
        Python translation of the JS decryptXml(xmlData).

        Returns:
            - decrypted xml_data (string) if checksum matches
            - None if encrypted but invalid / checksum mismatch / missing key
            - original xml_data if it didn't contain post_enc=
        """
        post_enc = "post_enc="
        idx_enc = xml_data.find(post_enc)  # JS: search(postEnc)
        if idx_enc >= 0:
            idx_enc = idx_enc + len(post_enc)

            post_chk = "&post_chk="
            idx_chk = xml_data.find(post_chk)  # JS: search(postChk)
            if idx_chk >= 0:
                # JS: chkSumPost = xmlData.substr(IdxChk + postChk.length);
                chk_sum_post = xml_data[idx_chk + len(post_chk):]

                # JS: xmlData = xmlData.substr(IdxEnc, (IdxChk - IdxEnc));
                xml_data = xml_data[idx_enc:idx_chk]

                session_key = self.get_set_session_key()
                if session_key is not None:
                    # JS: xmlData = rc4Decrypt(getSetSessionKey(), xmlData);
                    # If your post_enc payload is hex ciphertext (typical with your rc4()),
                    # use rc4_decrypt_hex. If it's not hex, swap to your own decrypt routine.
                    xml_data = self.rc4_decrypt_hex(session_key, xml_data)

                    # JS: chkSumCalc = postChkCalc(xmlData);
                    chk_sum_calc = self.post_chk_calc(xml_data)

                    # JS: chkSumCalc = parseInt(chkSumCalc, 16); chkSumCalc &= 65535;
                    chk_sum_calc = int(chk_sum_calc, 16) & 0xFFFF

                    # JS: chkSumPost = parseInt(chkSumPost, 16);
                    chk_sum_post = int(chk_sum_post, 16)

                    if chk_sum_post == chk_sum_calc:
                        return xml_data

            return None

        return xml_data



    def _http_post(self, path, data):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = data #urlencode(data)

        url = "{}/{}".format(self.base_url, path.lstrip("/"))
        try:
            return model.RestPost(url, headers, payload)
        except Exception:
            pass
            # return model.RestPost(url, headers, payload)

    def _get_temp_session(self):
        response = model.RestGet("{}/login_sdk.xml".format(self.base_url), {})
        xml = ET.fromstring(response)

        conn = xml.find(".//CONNECTION")
        dev = xml.find(".//DEVICE")

        if conn is None or dev is None:
            raise Exception("Atrium login response missing CONNECTION or DEVICE nodes")

        self.session_id = conn.get("session")
        self.serial = dev.get("serial")

        timeout_secs = _safe_int(conn.get("timeout"), 60)
        self.timeout_at = datetime.datetime.now() + datetime.timedelta(seconds=timeout_secs)
        self.session_key = hashlib.md5((self.serial + self.session_id).encode()).hexdigest().upper()

    def authenticate(self):
        self._get_temp_session()

        login_data = {
            "sid": self.session_id,
            "cmd": "login",
            "login_user": AtriumClient.rc4(self.session_key, self.username),
            "login_pass": hashlib.md5((self.session_key + self.password).encode()).hexdigest().upper(),
        }

        response = self._http_post("login_sdk.xml", login_data)
        xml = ET.fromstring(response)

        conn = xml.find(".//CONNECTION")
        dev = xml.find(".//DEVICE")
        if conn is None or dev is None:
            raise Exception("Atrium authentication failed")

        self.session_id = conn.get("session")
        self.serial = dev.get("serial")

        timeout_secs = _safe_int(conn.get("timeout"), 60)
        self.timeout_at = datetime.datetime.now() + datetime.timedelta(seconds=timeout_secs)
        self.session_key = hashlib.md5((self.serial + self.session_id).encode()).hexdigest().upper()

        return True

    def _ensure_session(self):
        if not self.session_id:
            self.authenticate()
            return

        if self.timeout_at is None:
            self.authenticate()
            return

        # Refresh if session is about to expire.
        if datetime.datetime.now() >= (self.timeout_at - datetime.timedelta(seconds=15)):
            self.authenticate()

    def _post_cmd(self, path, cmd, extra_data=None):
        self._ensure_session()

        data = {
            "sid": self.session_id,
            "cmd": cmd,
        }
        if extra_data:
            data.update(extra_data)

        response = self.decrypt_xml(self.session_id, self._http_post(path, data))

        if "INVALID" in _normalize_text(response).upper() and "SESSION" in _normalize_text(response).upper():
            self.authenticate()
            data["sid"] = self.session_id
            response = self.decrypt_xml(self.session_id, self._http_post(path, data))

        print(cmd)
        print(self.session_id)
        print(response)

        return response

    def get_schedules(self):
        response = self._post_cmd("schedules.xml", "list_schedules")
        xml = ET.fromstring(response)
        schedules = []
        for schedule in xml.findall(".//SCHEDULE"):
            schedules.append({
                "id": _normalize_text(schedule.get("id")),
                "name": _normalize_text(schedule.get("name")) or "Unnamed Schedule",
            })
        return schedules

    def get_events(self, schedule_id):
        response = self._post_cmd("events_sdk.xml", "list_events", {"schedule_id": schedule_id})
        xml = ET.fromstring(response)

        events = []
        for event in xml.findall(".//EVENT"):
            events.append({
                "event_id": _normalize_text(event.get("id") or event.get("event_id")),
                "name": _normalize_text(event.get("name")),
                "start_time": _normalize_text(event.get("start_time")),
                "end_time": _normalize_text(event.get("end_time")),
                "schedule_id": _normalize_text(schedule_id),
            })
        return events

    def add_event(self, schedule_id, event):
        data = {
            "schedule_id": schedule_id,
            "event_id": event["event_id"],
            "name": event["name"],
            "start_time": event["start_time"],
            "end_time": event["end_time"],
        }

        response = self._post_cmd("events_sdk.xml", "add_event", data)
        if "SUCCESS" in _normalize_text(response).upper():
            return True, response

        response = self._post_cmd("events_sdk.xml", "add_events", data)
        return "SUCCESS" in _normalize_text(response).upper(), response

    def remove_event(self, schedule_id, event_id):
        data = {
            "schedule_id": schedule_id,
            "event_id": event_id,
            "event_ids": event_id,
        }

        response = self._post_cmd("events_sdk.xml", "remove_event", data)
        if "SUCCESS" in _normalize_text(response).upper():
            return True, response

        response = self._post_cmd("events_sdk.xml", "remove_events", data)
        return "SUCCESS" in _normalize_text(response).upper(), response


def get_atrium_client():
    global _atrium_client

    if _atrium_client is None:
        base_url = _normalize_text(model.Setting("AtriumApiUrl", ""))
        username = _normalize_text(model.Setting("AtriumApiUser", ""))
        password = _normalize_text(model.Setting("AtriumApiPassword", ""))

        if not base_url or not username or not password:
            raise Exception("Atrium credentials are missing")

        _atrium_client = AtriumClient(base_url, username, password)
        _atrium_client.authenticate()

    return _atrium_client


def has_valid_credentials():
    try:
        print("here1")
        get_atrium_client().get_schedules()
        return True
    except Exception:
        return False


def has_configuration():
    config = get_config()
    return (
            "systems" in config
            and "atrium" in config["systems"]
            and "devices" in config
            and "atrium" in config["devices"]
            and len(config["devices"]["atrium"]) > 0
    )


def get_mapping_defaults():
    return {
        "minutesBefore": 0,
        "minutesAfter": 0,
    }


def handle_config_save(schedules):
    config = get_config()
    if "devices" not in config:
        config["devices"] = {}
    if "atrium" not in config["devices"]:
        config["devices"]["atrium"] = {}
    if "systems" not in config:
        config["systems"] = []
    if "atrium" not in config["systems"]:
        config["systems"].append("atrium")

    schedule_lookup = {s["id"]: s for s in schedules}

    by_reservable = {}
    used_schedules = set()

    for key in Data.Keys():
        if not key.startswith("map|"):
            continue

        rid = key.split("|", 1)[1]
        sid = _normalize_text(Data[key])
        if not sid:
            continue
        if sid not in schedule_lookup:
            continue
        if sid in used_schedules:
            continue

        minutes_before = _safe_int(Data.get("before|{}".format(rid), 0), 0)
        minutes_after = _safe_int(Data.get("after|{}".format(rid), 0), 0)

        by_reservable[rid] = {
            "scheduleId": sid,
            "scheduleName": schedule_lookup[sid]["name"],
            "config": {
                "minutesBefore": minutes_before,
                "minutesAfter": minutes_after,
            },
        }
        used_schedules.add(sid)

    config["devices"]["atrium"] = by_reservable
    save_config(config)


def get_local_events(reservable_id, minutes_before, minutes_after):
    """Get one week of local reservation windows for a single resource."""

    sql = """
    WITH Reses as (
        SELECT r.MeetingId,
               MIN(DATEADD(MINUTE, {1}, r.ReservationStart)) as DeviceStart,
               MAX(DATEADD(MINUTE, {2}, r.ReservationEnd)) as DeviceEnd
        FROM Reservations r
        WHERE r.ReservationEnd > DATEADD(DAY, -1, GETDATE())
          AND r.ReservationStart < DATEADD(DAY, 7, GETDATE())
          AND r.ReservableId = {0}
        GROUP BY r.MeetingId
    )
    SELECT r.*, COALESCE(NULLIF(m.Description, ''), o.OrganizationName) as Name, m.*
    FROM Reses r
        JOIN Meetings m ON r.MeetingId = m.MeetingId
        JOIN Organizations o ON m.OrganizationId = o.OrganizationId
    WHERE m.Canceled = 0;
    """.format(_safe_int(reservable_id, -1), -1 * _safe_int(minutes_before, 0), _safe_int(minutes_after, 0))

    return q.QuerySql(sql)


def split_event_by_midnight(start_dt, end_dt):
    """Split a reservation window into one-or-more day-bounded segments."""

    segments = []

    if end_dt <= start_dt:
        return segments

    cursor = start_dt
    while cursor.Date < end_dt.Date:
        midnight = cursor.Date.AddDays(1)
        segments.append((cursor, midnight))
        cursor = midnight

    segments.append((cursor, end_dt))
    return segments


def transform_local_events_to_atrium_events(local_events, schedule_id):
    transformed = []

    for ev in local_events:
        segments = split_event_by_midnight(ev.DeviceStart, ev.DeviceEnd)
        if len(segments) == 0:
            continue

        base_event_id = "Mtg-{}-{}".format(ev.MeetingId, schedule_id)
        clean_name = _ascii_text(ev.Name, "Meeting {}".format(ev.MeetingId))

        for idx, segment in enumerate(segments):
            seg_start = segment[0]
            seg_end = segment[1]
            event_id = base_event_id
            if len(segments) > 1:
                event_id = "{}-{}".format(base_event_id, idx + 1)

            transformed.append({
                "event_id": event_id,
                "name": clean_name,
                "start_time": seg_start.ToString("yyyy-MM-dd HH:mm:ss"),
                "end_time": seg_end.ToString("yyyy-MM-dd HH:mm:ss"),
                "schedule_id": schedule_id,
            })

    return transformed


def _event_signature(event):
    return "|".join(
        [
            _normalize_text(event.get("name", "")),
            _normalize_text(event.get("start_time", "")),
            _normalize_text(event.get("end_time", "")),
        ]
    )


def get_schedule_diffs():
    global _events_to_add, _events_to_remove

    if _events_to_add is None or _events_to_remove is None:
        events_to_add = []
        events_to_remove = []

        config = get_config()
        mappings = config.get("devices", {}).get("atrium", {})

        client = get_atrium_client()

        for reservable_id, mapping in mappings.items():
            schedule_id = _normalize_text(mapping.get("scheduleId", ""))
            if not schedule_id:
                continue

            cfg = mapping.get("config", {})
            minutes_before = _safe_int(cfg.get("minutesBefore", 0), 0)
            minutes_after = _safe_int(cfg.get("minutesAfter", 0), 0)

            local_events = get_local_events(reservable_id, minutes_before, minutes_after)
            desired_events = transform_local_events_to_atrium_events(local_events, schedule_id)
            existing_events = client.get_events(schedule_id)

            desired_by_id = {e["event_id"]: e for e in desired_events}
            existing_by_id = {e["event_id"]: e for e in existing_events if e.get("event_id")}

            for event_id, desired in desired_by_id.items():
                existing = existing_by_id.get(event_id)
                if existing is None:
                    events_to_add.append(desired)
                    continue

                if _event_signature(existing) != _event_signature(desired):
                    events_to_remove.append(existing)
                    events_to_add.append(desired)

            for event_id, existing in existing_by_id.items():
                if event_id not in desired_by_id:
                    events_to_remove.append(existing)

        _events_to_add = events_to_add
        _events_to_remove = events_to_remove

    return _events_to_add, _events_to_remove


def apply_schedule_changes():
    global _events_to_add, _events_to_remove

    adds, removes = get_schedule_diffs()
    client = get_atrium_client()

    print("<h4>Applying Atrium sync changes</h4>")
    print("<p>Will remove {} and add {} events.</p>".format(len(removes), len(adds)))

    changes_left = _change_limit

    for ev in removes:
        if changes_left <= 0:
            break
        changes_left -= 1

        ok, response = client.remove_event(ev["schedule_id"], ev["event_id"])
        if not ok:
            print("<p><b>Failed remove:</b> {}</p>".format(html_escape(ev["event_id"])))
            print("<pre>{}</pre>".format(html_escape(_normalize_text(response))))

    for ev in adds:
        if changes_left <= 0:
            break
        changes_left -= 1

        ok, response = client.add_event(ev["schedule_id"], ev)
        if not ok:
            print("<p><b>Failed add:</b> {}</p>".format(html_escape(ev["event_id"])))
            print("<pre>{}</pre>".format(html_escape(_normalize_text(response))))

    print("<p>Applied up to {} changes this run.</p>".format(_change_limit - changes_left))

    _events_to_add = None
    _events_to_remove = None


def render_credentials_form():
    base_url = _normalize_text(model.Setting("AtriumApiUrl", ""))
    username = _normalize_text(model.Setting("AtriumApiUser", ""))
    password = _normalize_text(model.Setting("AtriumApiPassword", ""))

    model.Title = "Configure Atrium Integration"
    model.Header = "Configure Atrium Integration"

    print("<p>Set up CDVI Atrium API credentials and base URL.</p>")

    form = """
    <form action="/PyScriptForm/RoomAtriumIntegration?v=cred" method="POST">
        <table id="settings" class="table table-striped">
            <thead>
            <tr>
                <th>Setting</th>
                <th style="width:60%">Value</th>
            </tr>
            </thead>
            <tbody>
            <tr>
                <td><label for="base_url">Atrium Base URL (e.g. http://myatriumhost)</label></td>
                <td><input name="base_url" value="{0}" type="text" class="form-control" /></td>
            </tr>
            <tr>
                <td><label for="username">API Username</label></td>
                <td><input name="username" value="{1}" type="text" class="form-control" /></td>
            </tr>
            <tr>
                <td><label for="password">API Password</label></td>
                <td><input name="password" value="{2}" type="password" class="form-control" /></td>
            </tr>
            </tbody>
        </table>

        <input type="submit" value="Save" class="btn btn-primary" />
    </form>
    """.format(
        html_escape(base_url),
        html_escape(username),
        html_escape(password),
    )

    print(form)


def render_config_form():
    model.Title = "Configure Atrium Room Mapping"
    model.Header = "Configure Atrium Room Mapping"

    schedules = get_atrium_client().get_schedules()
    schedules.sort(key=lambda s: s.get("name", ""))

    reservables = [r for r in get_reservables(1) if r.IsReservable]
    config = get_config()
    mapping = config.get("devices", {}).get("atrium", {})

    rows = []
    for r in reservables:
        rid = str(r.ReservableId)
        current = mapping.get(rid, {})
        current_schedule = _normalize_text(current.get("scheduleId", ""))
        current_cfg = current.get("config", {})
        before_val = _safe_int(current_cfg.get("minutesBefore", 0), 0)
        after_val = _safe_int(current_cfg.get("minutesAfter", 0), 0)

        options = ["<option value=''>-- Not Mapped --</option>"]
        for s in schedules:
            sid = html_escape(s["id"])
            sname = html_escape(s["name"])
            selected = " selected" if s["id"] == current_schedule else ""
            options.append("<option value='{0}'{2}>{1}</option>".format(sid, sname, selected))

        rows.append(
            """
            <tr>
                <td>{name}</td>
                <td>
                    <select class="form-control" name="map|{rid}">
                        {options}
                    </select>
                </td>
                <td><input class="form-control" type="number" name="before|{rid}" value="{before}" /></td>
                <td><input class="form-control" type="number" name="after|{rid}" value="{after}" /></td>
            </tr>
            """.format(
                name=html_escape(r.Name),
                rid=rid,
                options="\n".join(options),
                before=before_val,
                after=after_val,
            )
        )

    print(
        """
        <p>Map each TouchPoint room to at most one Atrium schedule. A schedule can only be used once.</p>
        <form action="/PyScriptForm/RoomAtriumIntegration?v=config" method="POST">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Room</th>
                        <th>Atrium Schedule</th>
                        <th>Minutes Before</th>
                        <th>Minutes After</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            <input type="submit" value="Save" class="btn btn-primary" />
        </form>
        """.format(rows="\n".join(rows))
    )


def render_status_page():
    model.Title = "Atrium Integration Status"
    model.Header = "Atrium Integration Status"

    adds, removes = get_schedule_diffs()

    print("<p>Pending Atrium changes: {} adds, {} removes</p>".format(len(adds), len(removes)))

    apply_schedule_changes()

    # Display a compact diagnostic list after apply for transparency.
    post_adds, post_removes = get_schedule_diffs()
    print("<p>Remaining after apply: {} adds, {} removes</p>".format(len(post_adds), len(post_removes)))


if model.HttpMethod == "post" and Data.v == "cred":
    base_url = _normalize_text(Data.base_url)
    username = _normalize_text(Data.username)
    password = _normalize_text(Data.password)

    if base_url and username and password:
        model.SetSetting("AtriumApiUrl", base_url)
        model.SetSetting("AtriumApiUser", username)
        model.SetSetting("AtriumApiPassword", password)
        print("REDIRECT=/PyScript/RoomAtriumIntegration?v=config")
    else:
        render_credentials_form()

elif (not has_valid_credentials()) or Data.v == "cred":
    render_credentials_form()

elif model.HttpMethod == "post" and Data.v == "config":
    schedules = get_atrium_client().get_schedules()
    handle_config_save(schedules)
    print("REDIRECT=/PyScript/RoomAtriumIntegration?v=status")

elif Data.v == "config":
    render_config_form()

elif not has_configuration():
    print("REDIRECT=/PyScript/RoomAtriumIntegration?v=config")

elif Data.v == "status":
    render_status_page()

else:
    print("REDIRECT=/PyScript/RoomAtriumIntegration?v=status")