global model, Data, q

from urllib import urlencode
import xml.etree.ElementTree as ET
import json



site = ""
username = ""
password = ""
stats = None

# encode URL parameters
auth = urlencode({'username': username, 'password': password})

base_url = "https://{}/api.cgi?{}".format(site, auth)

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
    global stats
    if stats is None:
        atts = {
            'username': username,
            'password': password,
            'request': 'get',
            'object': 'Thermostat',
            'value': 'name;groupName;serialNo;description;schedule'
        }
        url = "https://{}/api.cgi?{}".format(site, urlencode(atts))
        stats = xml_str_to_dict(model.RestGet(url, {}))
    return stats

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
def get_thermostat_events(serial = None):

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
    return xml_str_to_dict(model.RestGet(url, {}))

# url = base_url + "&request=get&object=Thermostat&value=name;groupName;serialNo;description;schedule"

def has_valid_credentials():
    global username, password, site

    username = model.Setting("PelicanHvacEmail", "")
    password = model.Setting("PelicanHvacPassword", "")
    site = model.Setting("PelicanHvacSite", "")

    if not username or not password or not site:
        return False

    r = get_thermostats()
    return r['result']['success'] == "1"

def has_configuration():
    return False



if model.HttpMethod == "post" and Data.v == "credsave" and Data.username != "" and Data.password != "" and Data.site != "":
    model.SetSetting("PelicanHvacEmail", Data.username.strip())
    model.SetSetting("PelicanHvacPassword", Data.password.strip())
    model.SetSetting("PelicanHvacSite", Data.site.strip())

    print("REDIRECT=/PyScript/IntegrationPelican?v=config")

elif not has_valid_credentials():

    model.Title = "Configure Pelican HVAC Integration"
    model.Header = "Configure Pelican HVAC Integration"

    print("<p>Set up Pelican HVAC integration with Pelican account credentials.  We <b>strongly</b> recommend that you create a user within Pelican just for this purpose, separate from any human users.</p>")

    # language=html
    form = """
    <form action="/PyScriptForm/IntegrationPelican?v=credsave" method="POST">
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
    
    </form>
    """

    print(form.format(site, username, password))

elif Data.v == "config":
    model.Title = "Configure Pelican HVAC Integration"
    model.Header = "Configure Pelican HVAC Integration"

    stats = get_thermostats()
    stats = stats['result']['Thermostat']

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


    existingConfig = model.TextContent("IntegrationPelicanConfig.json") or "[]"

    header_row = ""
    option_row = ""

    for group in stats.keys():
        group_stats = stats[group]
        for stat in group_stats:
            header_row += "<th class=\"device\">{}<br /><span class=\"small\">{}</span></th>\n".format(stat.get('name', 'Unnamed'), stat.get('serialNo', 'Unnamed'))
            option_row += "<td>\n<input type=\"checkbox\" value=\"[1]\" name=\"{0}-[0]\"/>\n</td>\n".format(stat.get('serialNo', ''))


    reservables = get_reservables(1) # 1 = rooms

    reservable_dict = {r.ReservableId: r for r in reservables}
    children = {r.ReservableId: [] for r in reservables}
    for r in reservables:
        if r.ParentId in reservable_dict:
            children[r.ParentId].append(r)

    def generate_row(r, indents=0):
        indent_str = "&nbsp;" * (4 * indents)
        row = "<td>{}{}</td>\n".format(indent_str, r.Name)
        if r.IsReservable:
            row += option_row.replace('[0]', str(r.ReservableId))
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
    """.format(header_row, matrix)

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
    print("REDIRECT=/PyScript/IntegrationPelican?v=config")

else:


    # response = get_thermostats()
    # response = get_thermostat_events("7S3-GV44")

    response = get_thermostat_events()


    # response = model.RestGet(url, {})


    # response = xml_str_to_dict(response)

    print("<pre>")
    print(json.dumps(response, indent=4))
    print("</pre>")