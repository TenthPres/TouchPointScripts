"""
Read-only probe for a CDVI Atrium controller, for development use on a workstation (Python 3, not TouchPoint).

Credentials come from the environment (ATRIUM_URL, ATRIUM_USER, ATRIUM_PASS) so they never land in the repo or in
shell history.  Only a fixed allowlist of read-only requests can be sent; anything else is refused.

Usage:
    python atrium_probe.py get users.xml
    python atrium_probe.py post records_sdk.xml list_records obj_type=12
"""

import hashlib
import os
import re
import sys
import urllib.parse
import urllib.request

READ_ONLY_GETS = {"users.xml", "schedules.xml", "doors.xml", "areas.xml", "access_levels.xml", "users_T_user.xml",
                  "users_T_cards.xml", "cards.xml", "access_template.xml", "info_T_datetime.xml", "info_T_schlage.xml", "devices.xml"}
READ_ONLY_POSTS = set()  # the *_sdk.xml endpoints guessed by the first starter do not exist on this firmware (404)


def rc4(key, data):
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + ord(key[i % len(key)])) % 256
        s[i], s[j] = s[j], s[i]
    i = j = 0
    out = []
    for ch in data:
        i = (i + 1) % 256
        j = (j + s[i]) % 256
        s[i], s[j] = s[j], s[i]
        out.append(ch ^ s[(s[i] + s[j]) % 256])
    return bytes(out)


def rc4_hex_encrypt(key, text):
    return rc4(key, text.encode()).hex().upper()


def decrypt(key, body):
    """Responses are either plain XML or `post_enc=<hex>&post_chk=<sum>`."""
    if "post_enc=" not in body:
        return body
    m = re.search(r"post_enc=([0-9A-Fa-f]*)&post_chk=([0-9A-Fa-f]+)", body)
    if not m:
        return None
    plain = rc4(key, bytes.fromhex(m.group(1))).decode("latin-1")
    if sum(ord(c) for c in plain) & 0xFFFF != int(m.group(2), 16):
        return None
    return plain


class Probe:
    def __init__(self):
        self.base = os.environ.get("ATRIUM_URL", "http://10.60.0.200").rstrip("/")
        self.user = os.environ["ATRIUM_USER"]
        self.password = os.environ["ATRIUM_PASS"]

    def _req(self, path, data=None):
        url = "{}/{}".format(self.base, path)
        if data is not None:
            data = urllib.parse.urlencode(data).encode()
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=15) as r:
            return r.read().decode("latin-1")

    def login(self):
        temp = self._req("login_sdk.xml")
        sid = re.search(r'session="([^"]+)"', temp).group(1)
        serial = re.search(r'serial="([^"]+)"', temp).group(1)
        self.key = hashlib.md5((serial + sid).encode()).hexdigest().upper()
        resp = self._req("login_sdk.xml", {
            "sid": sid,
            "cmd": "login",
            "login_user": rc4_hex_encrypt(self.key, self.user),
            "login_pass": hashlib.md5((self.key + self.password).encode()).hexdigest().upper(),
        })
        self.sid = re.search(r'session="([^"]+)"', resp).group(1)
        err = re.search(r'err="([^"]*)"', resp)
        print("login: err={}".format(err.group(1) if err else "?"), file=sys.stderr)

    def get(self, path, params=None):
        if path not in READ_ONLY_GETS:
            raise SystemExit("refused: GET {} is not in the read-only allowlist".format(path))
        query = urllib.parse.urlencode(dict(params or {}, sid=self.sid))
        return decrypt(self.key, self._req("{}?{}".format(path, query)))

    def post(self, path, cmd, extra):
        if (path, cmd) not in READ_ONLY_POSTS:
            raise SystemExit("refused: {} {} is not in the read-only allowlist".format(path, cmd))
        data = {"sid": self.sid, "cmd": cmd}
        data.update(extra)
        return decrypt(self.key, self._req(path, data))


def sdk_read(self, serial, obj_type, rec, obj_id):
    """Official SDK record read (sdk.xml).  Only cmd="read" is ever sent from this probe."""
    body = ("<?xml version=\"1.0\" encoding=\"utf-8\"?><SDK xmlns='https://www.cdvi.ca/'><RECORDS><REC trans_id='1' "
            "cmd='read' sernum='{}' type='{}' id='{}' rec='{}'></REC></RECORDS></SDK>").format(serial, obj_type, obj_id, rec)
    enc = "post_enc={}&post_chk={:04X}".format(rc4(self.key, body.encode()).hex().upper(),
                                               sum(body.encode()) & 0xFFFF)
    url = "{}/sdk.xml?sid={}&_=1".format(self.base, self.sid)
    with urllib.request.urlopen(urllib.request.Request(url, data=enc.encode()), timeout=15) as r:
        return decrypt(self.key, r.read().decode("latin-1"))


Probe.sdk_read = sdk_read


def main(argv):
    p = Probe()
    p.login()
    if argv[0] == "get":
        print(p.get(argv[1], dict(a.split("=", 1) for a in argv[2:])))
    elif argv[0] == "sdk-read":
        print(p.sdk_read(*argv[1:5]))
    elif argv[0] == "post":
        print(p.post(argv[1], argv[2], dict(a.split("=", 1) for a in argv[3:])))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
