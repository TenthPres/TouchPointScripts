
# Pckgd
# Title: Pckgd
# Description: A module for managing packages and their updates.
# Updates from: github/TenthPres/TouchPointScripts/Pckgd/Pckgd.py
# Version: 0.0.2
# License: AGPL-3.0
# Author: James Kurtz

# Do not make edits to these files.  They will be overwritten during updates.

global model, q, Data
import json


class Pckgd:
    def __init__(self, type_id, name, body):
        self.filename = name
        self.body = body
        self.typeId = type_id
        self.headers = {}
        self.version = None
        self.parse_headers()
        self.determine_version()

    do_not_edit_demarcation = "========="

    @staticmethod
    def find_installed_packages():
        return [Pckgd(p.TypeId, p.Name, p.Body) for p in Pckgd.find_installed_files()]


    """ Finds all installed package contents in the system. """
    @staticmethod
    def find_installed_files():
        # noinspection SqlResolve
        return q.QuerySql("""
                          SELECT Name, Body, TypeId, * FROM Content c
                          WHERE (c.TypeId = 5 AND (
                                c.Body LIKE '%' + CHAR(10) + '# Pckgd%' OR
                                c.Body LIKE '# Pckgd%'))
                             OR (c.Body LIKE '%-- Pckgd%' AND c.TypeId = 4);
                          """)

    """ Parses the headers from the body of the content. """
    def parse_headers(self):
        lines = self.body.splitlines()
        for line in lines:
            if (self.typeId == 5 and line.strip().startswith('#')) or \
                    (self.typeId == 4 and line.strip().startswith('--')):
                parts = line[1:].split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()

                    # standardize casing of key
                    key = ' '.join(word.capitalize() for word in key.split())

                    # Only process headers not seen yet
                    if key not in self.headers:
                        self.headers[key] = value
            elif Pckgd.do_not_edit_demarcation in line:
                break
        return

    def get_action_buttons(self):
        buttons = []
        if 'Updates From' in self.headers:
            buttons.append({
                "label": "View Update Source",
                "url": self.get_update_source(),
                "class": "btn-primary"
            })

        return buttons

    def determine_version(self):
        # if version header is set AND it's a hex value or numbered, assume it's right.
        if 'Version' in self.headers and self.headers['Version'].strip() != "" and all(c in '0123456789abcdefABCDEF.' for c in self.headers['Version']):
            self.version = self.headers['Version']
        else:
            # find relevant part of body to hash
            b = self.body.split("Pckgd", 1)[1]
            if Pckgd.do_not_edit_demarcation in b:
                b = b.split(Pckgd.do_not_edit_demarcation, 1)[1]

            self.version = Pckgd.calculate_version_hash(b)
            self.headers['Version'] = self.version

    """ Sets or updates a header for a given body. """
    @staticmethod
    def set_header(body, key, value, type_id):
        lines = body.splitlines()
        new_lines = []
        header_found = False
        demarc_found = False
        for line in lines:
            if (type_id == 5 and line.strip().startswith('#')) or \
                    (type_id == 4 and line.strip().startswith('--')):
                parts = line[1:].split(':', 1)
                if len(parts) == 2 and parts[0].strip() == key and not header_found and not demarc_found:
                    new_lines.append("{} {}: {}".format(('#' if type_id == 5 else '--'), key, value))
                    header_found = True
                else:
                    new_lines.append(line)
            elif Pckgd.do_not_edit_demarcation in line:
                demarc_found = True # once we hit the demarcation, stop looking for headers

        if not header_found:  # Doesn't exist, so needs to be inserted.
            insert_index = 0
            pckgd_found = False
            for i, line in enumerate(new_lines):
                if "Pckgd" in line:
                    insert_index = i + 1  # keep iterating until we get to the Pckgd header
                    pckgd_found = True
                elif not pckgd_found:
                    insert_index = i + 1
                elif (type_id == 5 and line.strip().startswith('#')) or \
                        (type_id == 4 and line.strip().startswith('--')):
                    insert_index = i + 1
                elif pckgd_found:
                    break
                elif Pckgd.do_not_edit_demarcation in line:
                    insert_index = -1

            if insert_index > -1:
                new_lines.insert(insert_index, "{} {}: {}".format(('#' if type_id == 5 else '--'), key, value))

        return '\n'.join(new_lines)

    """ Calculates a version hash for a given piece of content.  This is compared to the version header. """
    @staticmethod
    def calculate_version_hash(content_body):
        import hashlib
        hash_object = hashlib.sha256(content_body.strip().encode('utf-8'))
        return hash_object.hexdigest()[:8]  # return first 8 characters of the hash


    def get_header_style(self):
        style = ""
        if "Header Image" in self.headers:
            style += "background-image: url('{}'); background-size: cover; ".format(self.headers['Header Image'])

        if 'Header Color' in self.headers:
            color = self.headers['Header Color']
        else:
            color = '#' + Pckgd.calculate_version_hash(self.filename)[:6]
        style += "background-color: {}; ".format(color)
        return style

    def get_update_source(self):
        if not 'Updates From' in self.headers:
            return None

        if self.headers['Updates From'].lower().startswith("github"):
            # TODO make this more efficient by caching default branch per repo and make use of other metadata, too.
            path = self.headers['Updates From'].split('/', 3)
            if len(path) == 4:  # some level of validation...

                # query github api to get default branch
                url = "https://api.github.com/repos/{}/{}".format(path[1], path[2])

                response = model.RestGet(url, {"Accept": "application/vnd.github.v3+json"})
                response = json.loads(response)

                default_branch = "main"
                if 'default_branch' in response:
                    default_branch = response['default_branch']

                return "https://raw.githubusercontent.com/{}/{}/refs/heads/{}/{}".format(path[1], path[2], default_branch, path[3])

        return None

    """ Checks if an update is available for this package. Note that this makes at least one, possibly more, HTTP requests. """
    def has_update_available(self):
        update_source = self.get_update_source()
        if not update_source:
            return False

        remote_content = model.RestGet(update_source, {})
        if remote_content == "404: Not Found":  # How Github specifically handles these things.
            raise Exception("Update source not found: {}".format(update_source))

        remote_pkg = Pckgd(self.typeId, self.filename, remote_content)
        return remote_pkg.version != self.version


if model.HttpMethod == "get" and Data.v == "":
    model.Header = "Package Manager"
    model.Title = "Package Manager"

    print("<h2>Installed Packages</h2>\n")
    print("<div class=\"section row\">\n")

    installed = Pckgd.find_installed_packages()
    if (not installed) or (len(installed) == 0):
        print("<p>No packages are currently installed.<p />\n")

    for p in installed:
        print("<div class=\"package col-12 col-sm-6 col-md-4 col-lg-3\">\n")
        print("<div class=\"package-header\" style=\"{}\"></div>\n".format(p.get_header_style()))

        print("<div class=\"package-body\">\n")
        name = p.headers['Name'] if 'Name' in p.headers else p.filename
        print("<h3>{}</h3>\n".format(name))
        if 'Description' in p.headers:
            print("<p>{}</p>\n".format(p.headers['Description']))

        try:
            if p.has_update_available():
                print("<p><strong>Update available!</strong></p>\n")
        except Exception as e:
            print("<p><strong>Error checking for updates: {}</strong></p>\n".format(str(e)))

        pkg_caps = []
        if 'Author' in p.headers:
            pkg_caps.append("by &nbsp;{}".format(p.headers['Author']))

        if 'License' in p.headers:
            pkg_caps.append("<span title=\"License\">{}</span>".format(p.headers['License']))

        pkg_caps.append("Version:&nbsp;{}".format(p.headers['Version']))

        print("<p class=\"package-caption\">{}</p>\n".format(" &bull; ".join(pkg_caps)))
        print("</div>\n")
        print("</div>\n")

    print("</div>\n")

    # language=html
    print("""
    <style>
    .package-header {
        width: 100%;
        padding-top: 25%;
    }
    .package-body {
        padding: 10px;
        border-width: 0 1px 1px;
        border-style: solid;
        border-color: #ccc;
    }
    div.package-body h3 {
        margin-top: 0;
    }
    p.package-caption {
        font-size: 0.75em;
        opacity: 0.7;
    }
    </style>
    """)