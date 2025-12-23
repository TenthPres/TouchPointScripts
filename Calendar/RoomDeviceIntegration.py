# Pckgd
# Title: Room Device Integration
# Description: Room Reservations controlling devices like thermostats
# Updates from: GitHub/TenthPres/TouchPointScripts/Calendar/RoomDeviceIntegration.py
# Author: James at Tenth


global model, Data, q

from urllib import urlencode
import xml.etree.ElementTree as ET
import json

site = ""
username = ""
password = ""
_stats = None

# encode URL parameters
auth = urlencode({'username': username, 'password': password})

base_url = "https://{}/api.cgi?{}".format(site, auth)

_existing_config = None

_events_to_add = None
_events_to_remove = None
_change_limit = 20

def xml_to_dict(element):
    # Convert an XML element and its children into a dictionary
    # if node has only text, make that the value alone.
    if element.text and element.text.strip() and not element.attrib and len(list(element)) == 0:
        return element.text.strip()

    node = {}
    # Add element attributes if present
    if element.attrib:
        node.update(element.attrib)
    # Add element text if present
    if element.text and element.text.strip():
        node['_text'] = element.text.strip()
    # Recursively process child elements
    for child in element:
        child_dict = xml_to_dict(child)
        if child.tag not in node:
            node[child.tag] = child_dict
        else:
            # Handle multiple children with the same tag
            if not isinstance(node[child.tag], list):
                node[child.tag] = [node[child.tag]]
            node[child.tag].append(child_dict)

    if node == {}:
        return None
    return node

def xml_str_to_dict(xml_string):
    # Parse the XML string
    root = ET.fromstring(xml_string)
    # Convert XML to dictionary
    return {root.tag: xml_to_dict(root)}

def get_thermostats():
    global _stats
    if _stats is None:
        atts = {
            'username': username,
            'password': password,
            'request': 'get',
            'object': 'Thermostat',
            'value': 'name;groupName;serialNo;description;schedule'
        }
        url = "https://{}/api.cgi?{}".format(site, urlencode(atts))
        stats = xml_str_to_dict(model.RestGet(url, {}))

        if not stats['result']['success'] == "1":
            raise Exception("Error retrieving thermostats: {}".format(r['result'].get('message', 'Unknown error')))

        _stats = stats['result']['Thermostat']
    return _stats

def get_config():
    """
    Retrieves the existing configuration for the Pelican HVAC integration.
    :return: dict representing the existing configuration.
    """

    import json
    global _existing_config

    if _existing_config is None:
        _existing_config = model.TextContent("IntegrationDeviceConfig.json") or "{}"
        _existing_config = json.loads(_existing_config)

    return _existing_config


def get_reservables(typ):
    return q.QuerySql("""
                      SELECT ReservableId,
                             ParentId,
                             COALESCE(BadgeColor, '#153aa8') as Color,
                             Name,
                             Description,
                             IsReservable,
                             IsEnabled,
                             IsCountable,
                             Quantity
                      FROM Reservable
                      WHERE ReservableTypeId = {}
                        AND IsDeleted = 0
                        AND IsEnabled = 1

                      ORDER BY ReservableTypeId, Name
                      ;
                      """.format(typ))

# Gets thermostat events for the thermostat with the given serial or for all thermostats if no serial is given.
def get_device_events(serial = None):

    selection = ['origin:External']

    if serial:
        selection.append('serialNo:{}'.format(serial))

    atts = {
        'username': username,
        'password': password,
        'request': 'get',
        'object': 'ThermostatEvent',
        'selection': ';'.join(selection),
        'value': 'eventId;title;startDate;startTime;endTime;heatSetting;coolSetting;fan;keypad;outsideVentilation;serialNo'
    }
    url = "https://{}/api.cgi?{}".format(site, urlencode(atts))
    data = model.RestGet(url, {})
    d = xml_str_to_dict(data).get('result', {}).get('ThermostatEvent', [])

    if not isinstance(d, list):
        return [d]

    return d

def get_local_events(did):

    config = get_config()
    if 'devices' not in config or 'pelican' not in config['devices'] or did not in config['devices']['pelican']:
        return []

    device_config = config['devices']['pelican'][did]
    if 'config' not in device_config:
        return []

    events = q.QuerySql("""
                        WITH Reses as (
                            SELECT r.MeetingId,
                                   MIN(DATEADD(MINUTE, {1}, r.ReservationStart)) as DeviceStart,
                                   MAX(DATEADD(MINUTE, {2}, r.ReservationEnd)) as DeviceEnd
                            FROM Reservations r
                            WHERE r.ReservationEnd > GETDATE()
                              AND r.ReservationStart < DATEADD(DAY, 7, GETDATE())
                              AND r.ReservableId IN ({0})
                            GROUP BY r.MeetingId
                        )
                        SELECT r.*, COALESCE(NULLIF(m.Description, ''), o.OrganizationName) as Name, m.* 
                        FROM Reses r
                            JOIN Meetings m ON r.MeetingId = m.MeetingId
                            JOIN Organizations o ON m.OrganizationId = o.OrganizationId
                        WHERE m.Canceled = 0;
                        """.format(
        ','.join(str(rid) for rid in device_config.get('reservableIds', [])),
        -1 * int(device_config.get('config', {}).get('minutesBefore', 0)),
        1 * int(device_config.get('config', {}).get('minutesAfter', 0))
    ))
    return events


def transform_local_events_to_device_events(local_events, did, device_config):
    events = []

    for e in local_events:  # TODO: deal with events that run past midnight (or are multi-day)
        events.append({
            'title': ''.join([c for c in e.Name if ord(c) < 128]), # remove non-ascii characters from title
            'eventId': "Mtg-{}-{}".format(e.MeetingId, did),
            'startDate': e.DeviceStart.ToString("yyyy-MM-dd"),  #  C# format date
            'startTime': e.DeviceStart.ToString("HH:mm"),
            'endTime': e.DeviceEnd.ToString("HH:mm"),
            'heatSetting': device_config.get('heatSetting', 66),
            'coolSetting': device_config.get('coolSetting', 74),
            'fan': device_config.get('fan', 'Auto'),
            'keypad': device_config.get('keypad', 'On'),
            'outsideVentilation': 'On',
            'serialNo': did
        })

    return events


def has_valid_credentials():
    global username, password, site

    username = model.Setting("PelicanHvacEmail", "")
    password = model.Setting("PelicanHvacPassword", "")
    site = model.Setting("PelicanHvacSite", "")

    if not username or not password or not site:
        return False

    try:
        get_thermostats()
    except Exception:
        return False
    return True

def has_configuration():
    config = get_config()
    return 'devices' in config and len(config['devices']) > 0 and 'systems' in config and 'pelican' in config['systems']


def get_device_config_defaults():
    return {
        'heatSetting': 66,
        'coolSetting': 74,
        'fan': 'Auto',
        'keypad': 'On',
        'minutesBefore': 0,
        'minutesAfter': 0,
        'system': 'Auto'
    }

def get_device_config_form(did, title, device_config):
    defaults = get_device_config_defaults()

    # apply default values if not in device config
    heatSetting = device_config.get('heatSetting', defaults['heatSetting'])
    coolSetting = device_config.get('coolSetting', defaults['coolSetting'])
    fan = device_config.get('fan', defaults['fan'])
    system = device_config.get('system', defaults['system'])
    keypad = device_config.get('keypad', defaults['keypad'])
    minutesBefore = device_config.get('minutesBefore', defaults['minutesBefore'])
    minutesAfter = device_config.get('minutesAfter', defaults['minutesAfter'])

    settings = [
        """
        <div class="form-group">
        <label for="{0}-system">System Setting:</label>
        <select name="{0}|system" id="{0}-system" class="form-control">
                <option value="Auto" {1}>Auto</option>
                <option value="Heat" {2}>Heat</option>
                <option value="Cool" {3}>Cool</option>
                <option value="Off" {4}>Off</option>
        </select>
        </div>
        """.format(did,
                   'selected' if system == 'Auto' else '',
                   'selected' if system == 'Heat' else '',
                   'selected' if system == 'Cool' else '',
                   'selected' if system == 'Off' else ''),
        """
        <div class="form-group">
        <label for="{0}-heatSetting">Heat Setpoint:</label>
        <input type="number" name="{0}|heatSetting" id="{0}-heatSetting" value="{1}" class="form-control" />
        </div>
        """.format(did, heatSetting),
        """
        <div class="form-group">
        <label for="{0}-coolSetting">Cool Setpoint:</label>
        <input type="number" name="{0}|coolSetting" id="{0}-coolSetting" value="{1}" class="form-control" />
        </div>
        """.format(did, coolSetting),
        """
        <div class="form-group">
        <label for="{0}-fan">Fan Setting:</label>
        <select name="{0}|fan" id="{0}-fan" class="form-control">
                <option value="Auto" {1}>Auto</option>
                <option value="On" {2}>On</option>
        </select>
        </div>
        """.format(did,
                   'selected' if fan == 'Auto' else '',
                   'selected' if fan == 'On' else ''),
        """
        <div class="form-group">
        <label for="{0}-keypad">Keypad:</label>
        <select name="{0}|keypad" id="{0}-keypad" class="form-control">
                <option value="On" {1}>On</option>
                <option value="Off" {2}>Off</option>
        </select>
        </div>
        """.format(did,
                   'selected' if keypad == 'On' else '',
                   'selected' if keypad == 'Off' else ''),
        """
        <div class="form-group">
        <label for="{0}-minutesBefore">Extend HVAC Minutes Before Setup:</label>
        <input type="number" name="{0}|minutesBefore" id="{0}-minutesBefore" value="{1}" class="form-control" />
        </div>
        """.format(did, minutesBefore),
        """
        <div class="form-group">
        <label for="{0}-minutesAfter">Extend HVAC Minutes After Teardown:</label>
        <input type="number" name="{0}|minutesAfter" id="{0}-minutesAfter" value="{1}" class="form-control" />
        </div>
        """.format(did, minutesAfter),
    ]

    return """
    <div class="well col-sm-6 col-md-4 col-lg-3">
    <fieldset>
        <legend>{0}</legend>
        
        {1}
    
    </fieldset>
    </div>
    """.format(title, '\n'.join(settings))

def handle_matrix_save():
    config = get_config()
    if 'devices' not in config:
        config['devices'] = {}
    if 'pelican' not in config['devices']:
        config['devices']['pelican'] = {}
    if 'systems' not in config:
        config['systems'] = []
    if 'pelican' not in config['systems']:
        config['systems'].append('pelican')

    # clear existing device reservable assignments and reset config to defaults
    for did in config['devices']['pelican'].keys():
        config['devices']['pelican'][did]['reservableIds'] = []
        config['devices']['pelican'][did]['reservableIds'] = []

    defaults = get_device_config_defaults()

    for key in Data.Keys():
        if '|' in key:
            did, rid = key.split('|', 1)

            # matrix checkboxes
            if rid.isnumeric():
                if did not in config['devices']['pelican']:
                    config['devices']['pelican'][did] = {}
                dc = config['devices']['pelican'][did]
                if 'reservableIds' not in dc:
                    dc['reservableIds'] = []
                if int(rid) not in dc['reservableIds']:
                    dc['reservableIds'].append(int(rid))
                continue

            # device configuration fields
            if rid in defaults.keys():
                if did not in config['devices']['pelican']:
                    config['devices']['pelican'][did] = {'config': {}}
                if 'config' not in config['devices']['pelican'][did]:
                    config['devices']['pelican'][did]['config'] = {}
                config['devices']['pelican'][did]['config'][rid] = Data[key]

    # remove devices with no reservables assigned
    devices_to_remove = []
    for did, dc in config['devices']['pelican'].items():
        if 'reservableIds' not in dc or len(dc['reservableIds']) == 0:
            devices_to_remove.append(did)
    for did in devices_to_remove:
        del config['devices']['pelican'][did]

    model.WriteContentText("IntegrationDeviceConfig.json", json.dumps(config, indent=4))

def get_schedule_diffs():

    global _events_to_add, _events_to_remove

    if _events_to_add is None or _events_to_remove is None:

        # compare device_events to transformed_events.  If details are different, remove and re-add.
        events_to_add = []
        events_to_remove = []

        config = get_config()
        for did in config['devices']['pelican']:
            device_events = get_device_events(did)
            device_config = config['devices']['pelican'][did]['config']
            transformed_events = transform_local_events_to_device_events(get_local_events(did), did, device_config)

            # find events to add
            for te in transformed_events:
                match = None
                for de in device_events:
                    if str(de['eventId']) == str(te['eventId']):
                        match = de
                        break
                if match is None:
                    events_to_add.append(te)
                else:
                    # compare details
                    for key in get_device_config_defaults().keys():
                        if str(match.get(key, '')) != str(te.get(key, '')):
                            events_to_remove.append(match)
                            events_to_add.append(te)
                            break

            # find events to remove
            for de in device_events:
                match = None
                for te in transformed_events:
                    if str(de['eventId']) == str(te['eventId']):
                        match = te
                        break
                if match is None:
                    events_to_remove.append(de)

        _events_to_add = events_to_add
        _events_to_remove = events_to_remove

    return _events_to_add, _events_to_remove


def has_changes_pending():
    adds, removes = get_schedule_diffs()
    return len(adds) > 0 or len(removes) > 0

def apply_schedule_changes():
    adds, removes = get_schedule_diffs()

    global _change_limit

    from pprint import pprint
    pprint(removes)

    for ev in removes:

        _change_limit = _change_limit - 1
        if _change_limit <= 0:
            break

        atts = {
            'username': username,
            'password': password,
            'request': 'set',
            'object': 'ThermostatEvent',
            'selection': 'serialNo:{};eventId:{}'.format(ev['serialNo'], ev['eventId']),
            'value': 'delete:Yes'
        }
        url = "https://{}/api.cgi?{}".format(site, urlencode(atts))

        print("<p>Request to {}</p>".format(url))  # TODO remove all this
        print("<pre>")
        print model.RestGet(url, {})
        print("</pre>")

    print "<hr />"

    pprint(adds)

    for ev in adds:
        _change_limit = _change_limit - 1
        if _change_limit <= 0:
            break

        values = {
            'title': ev['title'],
            'startDate': ev['startDate'],
            'startTime': ev['startTime'],
            'endTime': ev['endTime'],
            'heatSetting': ev['heatSetting'],
            'coolSetting': ev['coolSetting'],
            'fan': ev['fan'],
            'keypad': ev['keypad'],
            'outsideVentilation': ev['outsideVentilation'],
            'eventId': ev['eventId']
        }

        atts = {
            'username': username,
            'password': password,
            'request': 'set',
            'object': 'ThermostatEvent',
            'selection': 'serialNo:{}'.format(ev['serialNo']),
            'value': ';'.join(['{}:{}'.format(k, v) for k, v in values.items()])
        }
        try:
            url = "https://{}/api.cgi?{}".format(site, urlencode(atts))
        except Exception as e: # TODO remove, hopefully.
            print("<p>Error encoding URL for event addition: {}</p>".format(str(e)))
            pprint(atts)
            continue

        print("<p>Request to {}</p>".format(url))   # TODO remove all this
        print("<pre>")
        print model.RestGet(url, {})
        print("</pre>")

    global _events_to_add, _events_to_remove
    _events_to_add = None
    _events_to_remove = None


if model.HttpMethod == "post" and Data.v == "cred" and Data.username != "" and Data.password != "" and Data.site != "":
    model.SetSetting("PelicanHvacEmail", Data.username.strip())
    model.SetSetting("PelicanHvacPassword", Data.password.strip())
    model.SetSetting("PelicanHvacSite", Data.site.strip())

    print("REDIRECT=/PyScript/RoomDeviceIntegration?v=config")

elif not has_valid_credentials() or Data.v == "cred":

    model.Title = "Configure Pelican HVAC Integration"
    model.Header = "Configure Pelican HVAC Integration"

    print("<p>Set up Pelican HVAC integration with Pelican account credentials.  We <b>strongly</b> recommend that you create a user within Pelican just for this purpose, separate from any human users.</p>")

    # language=html
    form = """
           <form action="/PyScriptForm/RoomDeviceIntegration?v=cred" method="POST">
               <table id="settings" class="table table-striped">
                   <thead>
                   <tr>
                       <th>Setting</th>
                       <th style="width:50%">Value</th>
                   </tr>
                   </thead>
                   <tbody>
                   <tr>
                       <td><label for="site">Site Address (e.g. mychurch.officeclimatecontrol.net)</label></td>
                       <td><input name="site" value="{0}" type="text" /></td>
                   </tr>
                   <tr>
                       <td><label for="username">Email Address</label></td>
                       <td><input name="username" value="{1}" type="email" /></td>
                   </tr>
                   <tr>
                       <td><label for="password">Password</label></td>
                       <td><input name="password" value="{2}" type="text" /></td>
                   </tr>
                   </tbody>
               </table>

               <p>If you need to revisit these settings, they will be in the main TouchPoint settings in the "General" section.</p>

               <input type="submit" value="Save" class="btn btn-primary" />

           </form> \
           """

    print(form.format(site, username, password))

elif model.HttpMethod == "post" and Data.v == "config":
    handle_matrix_save()
    print("REDIRECT=/PyScript/RoomDeviceIntegration")

elif Data.v == "config":
    model.Title = "Configure Pelican HVAC Integration"
    model.Header = "Configure Pelican HVAC Integration"

    stats = get_thermostats()

    # sort by name alphabetically
    stats.sort(key=lambda x: x.get('name', ''))
    stats_count = len(stats)

    # group list of stats by groupName
    grouped_stats = {}
    for stat in stats:
        group_name = stat.get('groupName', 'Ungrouped')
        if group_name not in grouped_stats:
            grouped_stats[group_name] = []
        grouped_stats[group_name].append(stat)
    stats = grouped_stats

    header_row = ""
    option_row = ""
    device_settings = "<div class=\"row\">\n"

    for group in stats.keys():
        group_stats = stats[group]
        for stat in group_stats:
            header_row += "<th class=\"device\">{}<br /><span class=\"small\">{}</span></th>\n".format(stat.get('name', 'Unnamed'), stat.get('serialNo', 'Unnamed'))
            option_row += "<td>\n<input type=\"checkbox\" [{0}] name=\"{0}|[0]\"/>\n</td>\n".format(stat.get('serialNo', ''))
            device_settings += get_device_config_form(
                stat.get('serialNo', ''),
                stat.get('name', 'Unnamed'),
                get_config().get('devices', {}).get("pelican", {}).get(stat.get('serialNo'), {}).get("config", {})
            )

    device_settings += "</div>\n"
    reservables = get_reservables(1) # 1 = rooms

    reservable_dict = {r.ReservableId: r for r in reservables}
    children = {r.ReservableId: [] for r in reservables}
    for r in reservables:
        if r.ParentId in reservable_dict:
            children[r.ParentId].append(r)

    def generate_row(r, indents=0):
        row = "<td style=\"padding-left: {}px\">{}</td>\n".format((1 + indents) * 8, r.Name)
        if r.IsReservable:
            config = get_config()
            devices = get_thermostats()

            row += option_row.replace('[0]', str(r.ReservableId))

            for device in devices:
                did = device.get('serialNo', 'does not exist')

                device_is_assigned_to_reservable = False
                if 'devices' in config and 'pelican' in config['devices'] and did in config['devices']['pelican']: # the device has a configuration.
                    dc = config['devices']['pelican'][did]  # device configuration
                    if 'reservableIds' in dc and r.ReservableId in dc['reservableIds']:
                        device_is_assigned_to_reservable = True

                row = row.replace("[{}]".format(did), "checked" if device_is_assigned_to_reservable else "")

        else:
            row += "<td colspan=\"{}\"></td>\n".format(stats_count)
        mtx = "<tr>\n{}\n</tr>\n".format(row)
        for child in children[r.ReservableId]:
            mtx += generate_row(child, indents + 1)
        return mtx

    matrix = ""
    for r in reservables:
        if r.ParentId is None:
            matrix += generate_row(r)

    # language=html
    matrix = """
             <form action="/PyScriptForm/RoomDeviceIntegration?v=config" method="POST">
                 <table class="table table-striped">
                     <thead>
                     <tr>
                         <th>Room</th>
                         {}
                     </tr>
                     </thead>
                     <tbody>
                     {}
                     </tbody>
                 </table>

                 {}

                 <input type="submit" value="Save" class="btn btn-primary" />
             </form> \
             """.format(header_row, matrix, device_settings)

    print(matrix)

    # language=html
    print("""
          <style>
              th.device {
                  writing-mode: vertical-rl;
                  transform: rotate(180deg);
              }
          </style>
          """)

elif not has_configuration():
    print("REDIRECT=/PyScript/RoomDeviceIntegration?v=config")

elif Data.v == "status":
    model.Title = "Pelican HVAC Integration Status"
    model.Header = "Pelican HVAC Integration Status"

    config = get_config()

    if 'devices' in config and 'pelican' in config['devices']:
        devices = config['devices']['pelican']
    else:
        devices = {}

    apply_schedule_changes()

    from pprint import pprint
    pprint(get_schedule_diffs())

else:
    print("REDIRECT=/PyScript/RoomDeviceIntegration?v=status")

#