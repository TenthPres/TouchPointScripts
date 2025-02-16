import hashlib
import datetime
import urllib
import pprint
from cgi import escape
import xml.etree.ElementTree as ET

class Atrium:
    def __init__(self, base_url):
        self.base_url = base_url
        self.timeout = None
        self.serial = None
        self.username = None
        self.session_id = None
        self.session_key = None
        
    def __str__(self):
        return str({
            'base_url': self.base_url,
            'timeout': self.timeout,
            'serial': self.serial,
            'username': self.username
            })

    def get_temp_session_key(self):
        response = model.RestGet("{}/login_sdk.xml".format(self.base_url), {})
        xml = ET.fromstring(response)
        
        print "<h2>RestGet Login</h2>"
        print "<pre>" + escape(response) + "</pre>"

        self.session_id = xml.find(".//CONNECTION").get("session")
        self.serial = xml.find(".//DEVICE").get("serial")
        timeout_secs = int(xml.find(".//CONNECTION").get("timeout"))
        self.timeout = datetime.datetime.now() + datetime.timedelta(seconds=timeout_secs)
        self.session_key = hashlib.md5((self.serial + self.session_id).encode()).hexdigest().upper()
        
        print self.session_key

    def http_post(self, url, data):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = urllib.urlencode(data)
        print "<h2>RestPost</h2>"
        print "<pre>" + escape(data) + "</pre>"
        response = model.RestPostJson(url, headers, data)
        # response = model.RestPost(url, headers, data)
        print "<pre>" + escape(response) + "</pre>"
        # response = None
        return response

    @staticmethod
    def rc4(key, text):
        s = list(range(256))
        j = 0
        for i in range(256):
            j = (j + s[i] + ord(key[i % len(key)])) % 256
            s[i], s[j] = s[j], s[i]

        i = j = 0
        ct = ''
        for y in range(len(text)):
            i = (i + 1) % 256
            j = (j + s[i]) % 256
            s[i], s[j] = s[j], s[i]
            ct += '{:02X}'.format(ord(text[y]) ^ s[(s[i] + s[j]) % 256])

        return ct

    def authenticate(self, user, password):
        self.get_temp_session_key()

        data = {
            'sid': self.session_id,
            'cmd': 'login',
            'login_user': self.rc4(self.session_key, user),
            'login_pass': hashlib.md5((self.session_key + password).encode()).hexdigest().upper()
        }

        post_response = self.http_post("{}/login_sdk.xml".format(self.base_url), data)
        xml = ET.fromstring(post_response)

        self.session_id = xml.find(".//CONNECTION").get("session")
        self.serial = xml.find(".//DEVICE").get("serial")
        timeout_secs = int(xml.find(".//CONNECTION").get("timeout"))
        
        self.username = xml.find(".//SDK_CFG").get("username")

        try:
            self.timeout = datetime.datetime.now() + datetime.timedelta(seconds=timeout_secs)
        except Exception:
            self.timeout = datetime.datetime.now()
            
        print(self)

        self.session_key = hashlib.md5((self.serial + self.session_id).encode()).hexdigest().upper()
        return True
    
    def get_users(self):
        """Retrieves a list of all current users."""
        data = {
            'sid': self.session_id,
            'cmd': 'list_users',
        }
        response = self.http_post("{}/users_sdk.xml".format(self.base_url), data)
        
        try:
            xml = ET.fromstring(response)
        except Exception:
            pprint.pprint(response)
            return None
        
        users = []
        for user in xml.findall(".//USER"):
            users.append({
                "id": user.get("id"),
                "name": user.get("name"),
                "role": user.get("role"),
            })
        return users

    def get_schedules(self):
        """Retrieves a list of all schedules."""
        data = {
            'sid': self.session_id,
            'cmd': 'list_schedules',
        }
        response = self.http_post("{}/schedules_sdk.xml".format(self.base_url), data)
        xml = ET.fromstring(response)
        
        schedules = []
        for schedule in xml.findall(".//SCHEDULE"):
            schedules.append({
                "id": schedule.get("id"),
                "name": schedule.get("name"),
            })
        return schedules

    def get_events(self, schedule_id):
        """Retrieves a list of all events for a given schedule."""
        data = {
            'sid': self.session_id,
            'cmd': 'list_events',
            'schedule_id': schedule_id,
        }
        response = self.http_post("{}/events_sdk.xml".format(self.base_url), data)
        xml = ET.fromstring(response)
        
        events = []
        for event in xml.findall(".//EVENT"):
            events.append(AtriumEvent(
                event_id=event.get("id"),
                name=event.get("name"),
                start_time=event.get("start_time"),
                end_time=event.get("end_time"),
            ))
        return events

    def add_events(self, schedule_id, events):
        """Adds one or more events to a schedule."""
        if not isinstance(events, list):
            events = [events]

        event_data = []
        for event in events:
            event_data.append({
                "event_id": event.event_id,
                "name": event.name,
                "start_time": event.start_time,
                "end_time": event.end_time,
            })

        data = {
            'sid': self.session_id,
            'cmd': 'add_events',
            'schedule_id': schedule_id,
            'events': event_data,
        }
        response = self.http_post("{}/events_sdk.xml".format(self.base_url), data)
        return "SUCCESS" in response

    def remove_events(self, schedule_id, event_ids):
        """Removes one or more events from a schedule."""
        if not isinstance(event_ids, list):
            event_ids = [event_ids]

        data = {
            'sid': self.session_id,
            'cmd': 'remove_events',
            'schedule_id': schedule_id,
            'event_ids': event_ids,
        }
        response = self.http_post("{}/events_sdk.xml".format(self.base_url), data)
        return "SUCCESS" in response

# Example usage:
a = Atrium("http://publicUrlForAtrium")
a.authenticate("admin", "admin")

pprint.pprint(a.get_users())

# pprint.pprint(a.get_schedules())