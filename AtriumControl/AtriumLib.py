# Pckgd
# Title: Atrium Library
# Description: Shared client for the CDVI Atrium SDK, used by the other Atrium scripts.
# Updates from: GitHub/TenthPres/TouchPointScripts/AtriumControl/AtriumLib.py
# Version: 0.1.0
# License: AGPL-3.0
# Author: James at Tenth
# Editable: False

# Do not make edits to this file.  They will be overwritten during updates.

# Client for the official CDVI Atrium SDK (POST /sdk.xml).  Runs unchanged in TouchPoint (IronPython 2.7) and on a
# workstation (CPython 3), so keep it free of f-strings and other py3-only syntax.  See API-NOTES.md for how the
# protocol was worked out.

import datetime
import hashlib
import re
import xml.etree.ElementTree as ET

try:
    from urllib import urlencode, quote
except ImportError:
    from urllib.parse import urlencode, quote

SDK_NS = "https://www.cdvi.ca/"
NO_ACCESS_LEVEL = 65535  # an empty access level slot
NEVER = "FFFFFFFF"  # an activation / expiration that never applies
ACCESS_LEVEL_SLOTS = 5
MAX_ID_GAP = 100  # how many consecutive unused ids we tolerate before deciding a record table has ended


class AtriumError(Exception):
    pass


def _text(value):
    if value is None:
        return ""
    try:
        return unicode(value)  # noqa: F821  (py2)
    except NameError:
        return str(value)


def xml_attr(value):
    """Escape a value for use inside a single-quoted XML attribute, keeping the payload pure ASCII."""
    value = _text(value)
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;")
    return value.encode("ascii", "xmlcharrefreplace").decode("ascii")


def ascii_name(value, fallback=""):
    """Atrium names are stored as plain text; fold accents and drop anything else that isn't ASCII."""
    import unicodedata
    value = _text(value).strip()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return value.strip() or fallback


# ---------------------------------------------------------------------------------------------------------------------
# Crypto.  Requests and responses are RC4 (hex) with a 16-bit character-sum checksum.  Keys are always 7-bit text.
# ---------------------------------------------------------------------------------------------------------------------

def rc4_hex(key, text):
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + ord(key[i % len(key)])) % 256
        s[i], s[j] = s[j], s[i]
    i = j = 0
    out = []
    for ch in text:
        i = (i + 1) % 256
        j = (j + s[i]) % 256
        s[i], s[j] = s[j], s[i]
        out.append("{:02X}".format(ord(ch) ^ s[(s[i] + s[j]) % 256]))
    return "".join(out)


def rc4_unhex(key, hex_text):
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + ord(key[i % len(key)])) % 256
        s[i], s[j] = s[j], s[i]
    i = j = 0
    out = []
    for y in range(0, len(hex_text) - 1, 2):
        i = (i + 1) % 256
        j = (j + s[i]) % 256
        s[i], s[j] = s[j], s[i]
        out.append(chr(int(hex_text[y:y + 2], 16) ^ s[(s[i] + s[j]) % 256]))
    return "".join(out)


def checksum(text):
    return "{:04X}".format(sum(ord(c) for c in text) & 0xFFFF)


def encrypt_body(key, text):
    return "post_enc={}&post_chk={}".format(rc4_hex(key, text), checksum(text))


def decrypt_body(key, raw):
    """Returns plain text, or None if an encrypted payload fails its checksum."""
    if "post_enc=" not in raw:
        return raw
    m = re.search(r"post_enc=([0-9A-Fa-f]*)&post_chk=([0-9A-Fa-f]+)", raw)
    if not m:
        return None
    plain = rc4_unhex(key, m.group(1))
    if int(m.group(2), 16) != (sum(ord(c) for c in plain) & 0xFFFF):
        return None
    return plain


# ---------------------------------------------------------------------------------------------------------------------
# Time.  Users and cards carry real UTC epochs; schedules carry controller-local wall time expressed as if it were UTC.
# ---------------------------------------------------------------------------------------------------------------------

_EPOCH = datetime.datetime(1970, 1, 1)


def epoch_to_hex(seconds):
    return "{:08X}".format(int(seconds))


def hex_to_epoch(value):
    value = _text(value).strip()
    if not value or value.upper() == NEVER:
        return None
    return int(value, 16)


def datetime_to_epoch(dt):
    """For a naive datetime (already expressed in the zone the controller expects)."""
    delta = dt - _EPOCH
    return delta.days * 86400 + delta.seconds


def epoch_to_datetime(seconds):
    return _EPOCH + datetime.timedelta(seconds=int(seconds))


# ---------------------------------------------------------------------------------------------------------------------
# Transports.  A transport is f(method, url, body=None) -> response text.
# ---------------------------------------------------------------------------------------------------------------------

def urllib_transport(timeout=60):
    """For a workstation (CPython 3)."""
    import urllib.request

    def send(method, url, body=None):
        data = body.encode("ascii") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("latin-1")

    return send


def touchpoint_transport(model):
    """For TouchPoint's PyScript environment."""

    def send(method, url, body=None):
        if method == "GET":
            return model.RestGet(url, {})
        return model.RestPost(url, {"Content-Type": "application/x-www-form-urlencoded"}, body)

    return send


# ---------------------------------------------------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------------------------------------------------

class AtriumClient(object):
    def __init__(self, base_url, username, password, transport, master_serial=None, clock=datetime.datetime.now):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.transport = transport
        self.master_serial = master_serial
        self.clock = clock

        self.sid = None
        self.key = None
        self.expires = None
        self._trans = 0

    # -- session ---------------------------------------------------------------------------------------------------

    def _url(self, path, params=None):
        url = "{}/{}".format(self.base_url, path)
        if params:
            url += "?" + urlencode(params)
        return url

    def authenticate(self):
        temp = self.transport("GET", self._url("login_sdk.xml"))
        root = ET.fromstring(temp)
        conn = root.find(".//CONNECTION")
        dev = root.find(".//DEVICE")
        if conn is None or dev is None:
            raise AtriumError("Unexpected login response from Atrium")

        sid = conn.get("session")
        serial = dev.get("serial")
        key = hashlib.md5((serial + sid).encode("ascii")).hexdigest().upper()

        body = urlencode({
            "sid": sid,
            "cmd": "login",
            "login_user": rc4_hex(key, self.username),
            "login_pass": hashlib.md5((key + self.password).encode("utf-8")).hexdigest().upper(),
        })
        resp = ET.fromstring(self.transport("POST", self._url("login_sdk.xml"), body))
        cfg = resp.find(".//SDK_CFG")
        conn = resp.find(".//CONNECTION")
        # A failed login still answers 200; the tell is that no user is attached to the session.
        if cfg is None or conn is None or cfg.get("user_id") in (None, "-1") or conn.get("err") not in (None, "ok"):
            raise AtriumError("Atrium login failed (check the SDK account and that SDK login is enabled for it)")

        self.sid = conn.get("session")
        self.key = key
        self.master_serial = self.master_serial or serial
        timeout = int(conn.get("timeout") or 900)
        self.expires = self.clock() + datetime.timedelta(seconds=timeout)

    def _ensure_session(self):
        if self.sid is None or self.expires is None or self.clock() >= self.expires - datetime.timedelta(seconds=30):
            self.authenticate()

    # -- raw requests ----------------------------------------------------------------------------------------------

    def get_xml(self, path, params=None):
        """GET one of the controller's list pages (e.g. 'devices.xml').  Read-only."""
        self._ensure_session()
        p = dict(params or {})
        p["sid"] = self.sid
        raw = self.transport("GET", self._url(path, p))
        plain = decrypt_body(self.key, raw)
        if plain is None:
            raise AtriumError("Could not decrypt response from {}".format(path))
        return _parse(plain)

    def sdk(self, kind, attrs, data=None):
        """
        Sends one RECORDS/REC or COMMANDS/CMD request and returns the parsed response element.
        kind: 'REC' or 'CMD'.  attrs: ordered list of (name, value).  data: optional ordered list of (name, value).
        """
        self._ensure_session()
        self._trans += 1
        xml = self.build_request(kind, self._trans, attrs, data)
        raw = self.transport("POST", self._url("sdk.xml", {"_": self._trans, "sid": self.sid}),
                             encrypt_body(self.key, xml))
        plain = decrypt_body(self.key, raw)
        if plain is None:
            raise AtriumError("Could not decrypt SDK response")
        root = _parse(plain)
        node = root.find(".//" + kind)
        if node is None:
            raise AtriumError("SDK response had no {} element".format(kind))
        res = node.get("res")
        if res not in (None, "ok"):
            raise AtriumError("Atrium SDK error '{}' for {}".format(res, [a for a in attrs if a[0] != "trans_id"]))
        return node

    @staticmethod
    def build_request(kind, trans_id, attrs, data=None):
        group = "RECORDS" if kind == "REC" else "COMMANDS"
        head = " ".join("{}='{}'".format(k, xml_attr(v)) for k, v in [("trans_id", trans_id)] + list(attrs))
        if data:
            body = "<DATA {}/>".format(" ".join("{}='{}'".format(k, xml_attr(v)) for k, v in data))
        else:
            body = ""
        return ("<?xml version=\"1.0\" encoding=\"utf-8\"?><SDK xmlns='{ns}'><{g}><{k} {h}>{b}</{k}></{g}></SDK>"
                .format(ns=SDK_NS, g=group, k=kind, h=head, b=body))

    # -- records ---------------------------------------------------------------------------------------------------

    def read(self, serial, obj_type, rec, obj_id):
        node = self.sdk("REC", [("cmd", "read"), ("sernum", serial), ("type", obj_type), ("id", obj_id), ("rec", rec)])
        data = node.find("DATA")
        return dict(data.attrib) if data is not None else {}

    def read_range(self, serial, obj_type, rec, id_min, id_max):
        node = self.sdk("REC", [("cmd", "read"), ("sernum", serial), ("type", obj_type), ("id_min", id_min),
                                ("id_max", id_max), ("rec", rec)])
        return [dict(d.attrib) for d in node.findall("DATA")]

    def write(self, serial, obj_type, rec, obj_id, fields):
        """Writes the given fields to an existing record.  Only the named fields are sent."""
        self.sdk("REC", [("cmd", "write"), ("sernum", serial), ("type", obj_type), ("id", obj_id), ("rec", rec)],
                 sorted(fields.items()))

    def add(self, serial, obj_type, rec, fields):
        """Creates a record in the first free id and returns that id."""
        node = self.sdk("REC", [("cmd", "add"), ("sernum", serial), ("type", obj_type), ("rec", rec)],
                        sorted(fields.items()))
        data = node.find("DATA")
        new_id = data.get("id") if data is not None else node.get("id")
        if new_id is None:
            raise AtriumError("Atrium did not report the id of the new {}".format(obj_type))
        return int(new_id)

    def delete(self, serial, obj_type, rec, obj_id):
        self.sdk("REC", [("cmd", "delete"), ("sernum", serial), ("type", obj_type), ("id", obj_id), ("rec", rec)])

    # -- users -----------------------------------------------------------------------------------------------------

    def iter_records(self, obj_type, rec="cfg", serial=None, batch=25, only_used=True):
        """Walks a record table in batches until it runs out of used ids."""
        serial = serial or self.master_serial
        start = 0
        empty_run = 0
        while empty_run < MAX_ID_GAP:
            rows = self.read_range(serial, obj_type, rec, start, start + batch - 1)
            used = [r for r in rows if r.get("obj_status", "used") == "used"]
            for r in used:
                yield r
            empty_run = 0 if used else empty_run + batch
            start += batch

    def list_users(self):
        return [parse_user(r) for r in self.iter_records("user")]

    def get_user(self, user_id):
        return parse_user(self.read(self.master_serial, "user", "cfg", user_id))

    def add_user(self, first_name, last_name, access_levels=(), activation=None, expiration=None):
        fields = user_fields(first_name=first_name, last_name=last_name, access_levels=access_levels,
                             activation=activation, expiration=expiration, enabled=True)
        return self.add(self.master_serial, "user", "cfg", fields)

    def update_user(self, user_id, **changes):
        self.write(self.master_serial, "user", "cfg", user_id, user_fields(**changes))

    def list_access_levels(self):
        return [{"id": int(r["id"]), "label": r.get("label3", "")} for r in self.iter_records("access_lvl")]

    def list_schedules(self):
        return [{"id": int(r["id"]), "label": r.get("label3", "")} for r in self.iter_records("sched")]

    def list_cards(self):
        return [parse_card(r) for r in self.iter_records("card")]

    # -- schedules ---------------------------------------------------------------------------------------------------

    def get_schedule(self, sched_id):
        return parse_schedule(self.read(self.master_serial, "sched", "cfg", sched_id))

    def set_schedule_windows(self, sched_id, start, cycle_days, windows):
        """
        Replaces a schedule's periods.  Refuses the controller's built-in schedules (ids 0-5) and anything marked
        read-only or protected.  `start` is a naive datetime in the controller's local wall time.
        """
        current = self.read(self.master_serial, "sched", "cfg", sched_id)
        if sched_id <= LAST_BUILTIN_SCHEDULE or current.get("ro") == "1" or current.get("protect") == "1":
            raise AtriumError("Schedule {} is built in or protected and will not be modified".format(sched_id))
        self.write(self.master_serial, "sched", "cfg", sched_id, schedule_fields(start, cycle_days, windows))

    # -- doors, lockdown ---------------------------------------------------------------------------------------------

    def list_controllers(self):
        root = self.get_xml("devices.xml")
        out = [{"serial": self.master_serial, "name": "master"}]
        for d in root.findall(".//DEVICE"):
            out.append({"serial": d.get("sn"), "name": d.get("desc"), "online": d.get("status") == "1"})
        return out

    def list_doors(self):
        root = self.get_xml("doors.xml")
        return [{"serial": d.get("sn"), "id": int(d.get("id")), "name": d.get("name")} for d in root.findall(".//DOOR")]

    # UNVERIFIED: the shapes below follow the SDK's object tables (door: unlock/lock, lockdown: start/stop), but no
    # command has been sent to the production controller yet.  They exist so the first test is deliberate.

    def momentary_unlock(self, serial, door_id, seconds, confirm=False):
        """Unlocks one door for `seconds`, after which the controller relocks it by itself."""
        if confirm is not True:
            raise AtriumError("momentary_unlock requires confirm=True")
        seconds = int(seconds)
        if not 1 <= seconds <= 300:
            raise AtriumError("Unlock time must be between 1 and 300 seconds")
        self.sdk("CMD", [("cmd", "unlock"), ("sernum", serial), ("type", "door"), ("id", door_id)],
                 [("dword0", seconds)])

    def start_lockdown(self, confirm=False):
        if confirm is not True:
            raise AtriumError("start_lockdown requires confirm=True")
        self.sdk("CMD", [("cmd", "start"), ("sernum", self.master_serial), ("type", "lockdown"), ("id", 0)])

    def stop_lockdown(self, confirm=False):
        if confirm is not True:
            raise AtriumError("stop_lockdown requires confirm=True")
        self.sdk("CMD", [("cmd", "stop"), ("sernum", self.master_serial), ("type", "lockdown"), ("id", 0)])

    # -- wireless lock batteries -------------------------------------------------------------------------------------

    def wireless_lock_status(self):
        """
        Battery and link state for each enabled Allegion/Schlage wireless lock, across every controller that has a
        gateway.  The trouble flags are authoritative; the voltage is informational (see API-NOTES.md).
        """
        results = []
        for ctrl in self.list_controllers():
            serial = ctrl["serial"]
            if ctrl.get("online") is False:
                continue
            try:
                info = self.get_xml("info_T_schlage.xml", {"T_serial": serial})
            except AtriumError:
                continue
            for apm in info.findall(".//APM"):
                if apm.get("enable") != "1":
                    continue
                apm_id = int(apm.get("id"))
                status = self.read(serial, "ir_apm", "status", apm_id)
                trouble = self.read(serial, "ir_apm", "trouble", apm_id)
                results.append(parse_wireless_lock(serial, apm_id, apm.get("lbl", "").strip(), status, trouble))
        return results


def _parse(text):
    text = re.sub(r"\sxmlns=\"[^\"]*\"", "", text, count=1)  # the SDK declares a default namespace; we don't need it
    try:
        return ET.fromstring(text)
    except ET.ParseError:
        return ET.fromstring(re.sub(r"[^\x20-\x7E\r\n\t]", "?", text))


# ---------------------------------------------------------------------------------------------------------------------
# Record <-> dict helpers
# ---------------------------------------------------------------------------------------------------------------------

def parse_user(rec):
    levels = []
    for i in range(ACCESS_LEVEL_SLOTS):
        v = int(rec.get("word24_{}".format(i), NO_ACCESS_LEVEL))
        if v != NO_ACCESS_LEVEL:
            levels.append(v)
    first = rec.get("label3", "")
    last = rec.get("label4", "")
    return {
        "id": int(rec["id"]),
        "guid": rec.get("guid2", ""),
        "first_name": first,
        "last_name": last,
        "name": "{} {}".format(first, last).strip(),
        "enabled": rec.get("valid") == "1",
        "activation": hex_to_epoch(rec.get("utc_time22")),
        "expiration": hex_to_epoch(rec.get("utc_time23")),
        "access_levels": levels,
    }


def user_fields(first_name=None, last_name=None, access_levels=None, activation=None, expiration=None, enabled=None):
    """
    Builds the fields to write.  Only supplied arguments are included, so a write never clobbers something the caller
    didn't mean to touch.  `activation`/`expiration` are epoch seconds, or the string 'never' for expiration.
    """
    f = {}
    if first_name is not None:
        f["label3"] = ascii_name(first_name)[:32]
    if last_name is not None:
        f["label4"] = ascii_name(last_name)[:32]
    if access_levels is not None:
        levels = list(access_levels)
        if len(levels) > ACCESS_LEVEL_SLOTS:
            raise AtriumError("Atrium supports at most {} access levels per user".format(ACCESS_LEVEL_SLOTS))
        levels = levels + [NO_ACCESS_LEVEL] * (ACCESS_LEVEL_SLOTS - len(levels))
        for i, v in enumerate(levels):
            f["word24_{}".format(i)] = int(v)
    if activation is not None:
        f["utc_time22"] = epoch_to_hex(activation)
    if expiration is not None:
        f["utc_time23"] = NEVER if expiration == "never" else epoch_to_hex(expiration)
    if enabled is not None:
        f["valid"] = 1 if enabled else 0
    return f


def parse_card(rec):
    return {
        "id": int(rec["id"]),
        "label": rec.get("label3", ""),
        "user_id": int(rec.get("dword4", 0)),
        "number": "{}-{}".format(rec.get("hexv6", ""), rec.get("hexv5", "")),
        "enabled": rec.get("valid") == "1",
        "lost": rec.get("bit21") == "1",
        "stolen": rec.get("bit22") == "1",
        "activation": hex_to_epoch(rec.get("utc_time24")),
        "expiration": hex_to_epoch(rec.get("utc_time25")),
    }


SCHEDULE_PERIODS = 100  # periods a single schedule can hold
LAST_BUILTIN_SCHEDULE = 5  # Never, Always, Programming, Pin Required, Staff, Special


def normalize_windows(start, cycle_days, windows):
    """
    Turns (start, end) datetime pairs into sorted, merged (offset, offset) second pairs inside one schedule cycle.
    Windows are clipped to the cycle, and overlapping or touching windows are merged.
    """
    span = int(cycle_days) * 86400
    base = datetime_to_epoch(start)
    clipped = []
    for w_start, w_end in windows:
        a = max(datetime_to_epoch(w_start) - base, 0)
        b = min(datetime_to_epoch(w_end) - base, span)
        if b > a:
            clipped.append([a, b])
    clipped.sort()
    merged = []
    for a, b in clipped:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [(a, b) for a, b in merged]


def schedule_fields(start, cycle_days, windows):
    periods = normalize_windows(start, cycle_days, windows)
    if len(periods) > SCHEDULE_PERIODS:
        raise AtriumError("{} periods do not fit in one schedule (limit {})".format(len(periods), SCHEDULE_PERIODS))
    f = {"utc_time4": epoch_to_hex(datetime_to_epoch(start)), "dword5": int(cycle_days) * 86400}
    for i in range(SCHEDULE_PERIODS):
        a, b = periods[i] if i < len(periods) else (0, 0)
        f["dword6_{}".format(i)] = a
        f["dword7_{}".format(i)] = b
    return f


def parse_schedule(rec):
    periods = []
    for i in range(SCHEDULE_PERIODS):
        a, b = int(rec.get("dword6_{}".format(i), 0)), int(rec.get("dword7_{}".format(i), 0))
        if b > a:
            periods.append((a, b))
    return {
        "id": int(rec["id"]),
        "label": rec.get("label3", ""),
        "start": epoch_to_datetime(int(rec.get("utc_time4", "0"), 16)),
        "cycle_seconds": int(rec.get("dword5", 0)),
        "periods": periods,
        "protected": rec.get("ro") == "1" or rec.get("protect") == "1",
    }


def parse_wireless_lock(serial, apm_id, label, status, trouble):
    whole = int(status.get("byte0", 0))
    frac = int(status.get("byte1", 0))
    return {
        "serial": serial,
        "id": apm_id,
        "label": label,
        "online": status.get("bit5") == "1",
        "battery_low": trouble.get("bit1") == "1",
        "battery_critical": trouble.get("bit2") == "1",
        "rf_loss": trouble.get("bit5") == "1",
        # Assumed 1/256 V resolution for the fractional byte; unconfirmed, so informational only.
        "volts": round(whole + frac / 256.0, 2),
        "raw_volts": (whole, frac),
    }
