# Pckgd
# Title: Pckgd, A Package Manager
# Description: A module for managing packages and their updates.
# Updates from: GitHub/TenthPres/TouchPointScripts/Pckgd/Pckgd.py
# Version: 0.0.7
# License: AGPL-3.0
# Author: James at Tenth
# Editable: False

# Do not make edits to this file.  They will be overwritten during updates.

global model, q, Data
import json
import time


class Pckgd:
    def __init__(self, type_id, name, body):
        self.filename = name
        self.body = body
        self.typeId = type_id
        self.headers = {}
        self.version = None
        self._has_update_available = None
        self.parse_headers()
        self.determine_version()
        self.add_dependencies()

    def __del__(self):
        Pckgd._save_meta_if_dirty()

    do_not_edit_demarcation = "========="
    dependents = {}
    _saved_meta = None

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
                prefix_chars = 1 if self.typeId == 5 else 2
                line = line.strip()
                parts = line[prefix_chars:].split(':', 1)
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

        if 'Editable' in self.headers and self.headers['Editable'].lower() in ['false', '0', 'no', 'off']:
            self.headers['Editable'] = False
        else:
            self.headers['Editable'] = True

        return

    def get_action_buttons(self):
        buttons = []

        if self.typeId == 5:
            buttons.append("""
            <a href="/PyScript/{}" class="btn btn-default">Run</a>
            """.format(self.filename))
        elif self.typeId == 4:
            buttons.append("""
            <a href="/RunScript/{}" class="btn btn-default">Run</a>
            """.format(self.filename))

        link = self.get_repo_link()
        if link:
            buttons.append("""
            <a href="{}" class="btn btn-default" target="_blank" title="View on GitHub"><i class="fa fa-github"></i></a>
            """.format(link))

        if self.has_update_available():
            buttons.append("""
            <a href="/PyScript/Pckgd?v=update&pkg={}" class="btn btn-primary">Update</a>
            """.format(self.filename_with_extension()))

        return "\n".join(buttons)

    def determine_version(self):
        # if version header is set AND it's a hex value or numbered, assume it's right.
        if 'Version' in self.headers and self.headers['Version'].strip() != "" and all(c in '0123456789abcdefABCDEF.' for c in self.headers['Version']):
            self.version = self.headers['Version']
        else:
            # find relevant part of body to hash
            b = self.body
            if "Pckgd" in self.body:
                b = b.split("Pckgd", 1)[1]
            if Pckgd.do_not_edit_demarcation in b:
                b = b.split(Pckgd.do_not_edit_demarcation, 1)[1]

            b = b.strip().replace('\r\n', '\n').replace('\r', '\n')

            self.version = Pckgd.calculate_version_hash(b)
            self.headers['Version'] = self.version


    def add_dependencies(self):
        if 'Requires' in self.headers:
            dependencies = [d.strip() for d in self.headers['Requires'].split(',')]
            for dep in dependencies:
                if dep not in Pckgd.dependents:
                    Pckgd.dependents[dep] = []
                Pckgd.dependents[dep].append(self.filename_with_extension())


    def dependents_list(self):
        if self.filename_with_extension() in Pckgd.dependents:
            return Pckgd.dependents[self.filename_with_extension()]
        return []

    def dependencies_list(self):
        if 'Requires' in self.headers:
            return [d.strip() for d in self.headers['Requires'].split(',')]
        return []

    def has_dependents(self):
        deps = self.dependents_list()
        return len(deps)

    def has_dependencies(self):
        return len(self.dependencies_list())

    def dependencies_with_updates_available(self):
        updates = []
        for dep in self.dependencies_list():
            dep_pkg = None
            for p in Pckgd.find_installed_packages():
                if p.filename_with_extension() == dep:
                    dep_pkg = p
                    break
            if dep_pkg and dep_pkg.has_update_available():
                updates.append((dep, dep_pkg.has_update_available()))
        return updates

    def get_repo_link(self):
        if not 'Updates From' in self.headers:
            return None

        if self.headers['Updates From'].lower().startswith("github"):
            path = self.headers['Updates From'].split('/', 3)
            if len(path) == 4:  # some level of validation...
                github_meta = Pckgd._get_github_repo_metadata(path[1] + "/" + path[2])

                default_branch = "main"
                if 'default_branch' in github_meta:
                    default_branch = github_meta['default_branch']

                return "https://github.com/{}/{}/blob/{}/{}".format(path[1], path[2], default_branch, path[3])
        return None


    def filename_with_extension(self):
        if self.typeId == 5:
            return self.filename + ".py"
        elif self.typeId == 4:
            return self.filename + ".sql"
        else:
            return self.filename

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
                new_lines.append(line)
            else:
                new_lines.append(line)

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
            path = self.headers['Updates From'].split('/', 3)
            if len(path) == 4:  # some level of validation...
                github_meta = Pckgd._get_github_repo_metadata(path[1] + "/" + path[2])

                default_branch = "main"
                if 'default_branch' in github_meta:
                    default_branch = github_meta['default_branch']

                return "https://raw.githubusercontent.com/{}/{}/refs/heads/{}/{}".format(path[1], path[2], default_branch, path[3])

        return None

    def name(self):
        return self.headers['Title'] if 'Title' in self.headers else model.SpaceCamelCase(self.filename)

    """ Checks if an update is available for this package. Note that this makes at least one, possibly more, HTTP requests. """
    def has_update_available(self):
        if self._has_update_available is None:

            update_source = self.get_update_source()
            if not update_source:
                self._has_update_available = False
                return self._has_update_available

            remote_content = model.RestGet(update_source, {})
            if remote_content == "404: Not Found":  # How GitHub specifically handles these things.
                self._has_update_available = False
                raise Exception("Update source not found: {}".format(update_source))

            remote_pkg = Pckgd(self.typeId, self.filename, remote_content)
            if remote_pkg.version != self.version:
                self._has_update_available = remote_pkg.version
            else:
                self._has_update_available = False
        return self._has_update_available

    @staticmethod
    def _get_saved_meta():
        if Pckgd._saved_meta is None:
            saved_meta = model.TextContent("PckgdCache.json")
            if saved_meta.strip() == "":
                Pckgd._saved_meta = {}
            else:
                Pckgd._saved_meta = json.loads(saved_meta)
        return Pckgd._saved_meta

    @staticmethod
    def _get_github_repo_metadata(repo_path, bypass_cache=False):
        meta = Pckgd._get_saved_meta()

        if not "github_repo_meta" in meta:
            meta["github_repo_meta"] = {}

        if not repo_path in meta["github_repo_meta"]:
            meta["github_repo_meta"][repo_path] = {}

        if '_expires' not in meta["github_repo_meta"][repo_path] or meta["github_repo_meta"][repo_path]['_expires'] < time.time() or bypass_cache:
            # query GitHub api to get default branch and other such stuff
            url = "https://api.github.com/repos/{}".format(repo_path)
            response = model.RestGet(url, {"Accept": "application/vnd.github.v3+json"})
            meta["github_repo_meta"][repo_path]['data'] = json.loads(response)
            meta["github_repo_meta"][repo_path]['_expires'] = time.time() + 86400  # cache for 1 day
            meta['_dirty'] = True

        return meta["github_repo_meta"][repo_path]['data']

    @staticmethod
    def _save_meta_if_dirty():
        meta = Pckgd._get_saved_meta()
        if '_dirty' in meta and meta['_dirty']:
            del meta['_dirty']
            model.WriteContentText("PckgdCache.json", json.dumps(meta, indent=2))


    @staticmethod
    def _merge_variables(local_preamble, github_preamble, type_id):
        """
        Intelligently merge variable sections:
        - Keep user's customized values
        - Add new variables from GitHub
        - Preserve user's custom variables not in GitHub
        - Preserve comments and structure from GitHub
        - Handle multi-line assignments (lists, dicts, strings)
        """
        import re

        comment_char = '#' if type_id == 5 else '--'

        # Enhanced pattern: handles simple assignments including multi-line
        var_pattern = r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)$'

        local_vars = {}
        github_vars = {}
        local_lines = []
        github_lines = []

        # Track multi-line assignments
        current_var = None
        current_lines = []

        # Parse local preamble
        for line in local_preamble.split('\n'):
            match = re.match(var_pattern, line)
            if match:
                # Save previous multi-line var if any
                if current_var and current_lines:
                    local_vars[current_var] = '\n'.join(current_lines)

                var_name = match.group(2)
                current_var = var_name
                current_lines = [line]

                # Check if this might be multi-line (unclosed brackets/quotes)
                value = match.group(3).strip()
                if value.count('(') > value.count(')') or \
                   value.count('[') > value.count(']') or \
                   value.count('{') > value.count('}') or \
                   (value.count('"') % 2 == 1) or \
                   (value.count("'") % 2 == 1 and not value.endswith("'")):
                    # Multi-line, keep accumulating
                    pass
                else:
                    # Single line, save it
                    local_vars[var_name] = line
                    local_lines.append(('var', var_name, line))
                    current_var = None
                    current_lines = []
            elif current_var:
                # Continuation of multi-line assignment
                current_lines.append(line)
                # Check if closing
                if ')' in line or ']' in line or '}' in line or '"' in line or "'" in line:
                    local_vars[current_var] = '\n'.join(current_lines)
                    local_lines.append(('var', current_var, '\n'.join(current_lines)))
                    current_var = None
                    current_lines = []
            else:
                local_lines.append(('other', None, line))

        # Save any remaining multi-line var
        if current_var and current_lines:
            local_vars[current_var] = '\n'.join(current_lines)
            local_lines.append(('var', current_var, '\n'.join(current_lines)))

        # Parse GitHub preamble (same logic)
        current_var = None
        current_lines = []

        for line in github_preamble.split('\n'):
            match = re.match(var_pattern, line)
            if match:
                if current_var and current_lines:
                    github_vars[current_var] = '\n'.join(current_lines)

                var_name = match.group(2)
                current_var = var_name
                current_lines = [line]

                value = match.group(3).strip()
                if value.count('(') > value.count(')') or \
                   value.count('[') > value.count(']') or \
                   value.count('{') > value.count('}') or \
                   (value.count('"') % 2 == 1) or \
                   (value.count("'") % 2 == 1 and not value.endswith("'")):
                    pass
                else:
                    github_vars[var_name] = line
                    github_lines.append(('var', var_name, line))
                    current_var = None
                    current_lines = []
            elif current_var:
                current_lines.append(line)
                if ')' in line or ']' in line or '}' in line or '"' in line or "'" in line:
                    github_vars[current_var] = '\n'.join(current_lines)
                    github_lines.append(('var', current_var, '\n'.join(current_lines)))
                    current_var = None
                    current_lines = []
            else:
                github_lines.append(('other', None, line))

        if current_var and current_lines:
            github_vars[current_var] = '\n'.join(current_lines)
            github_lines.append(('var', current_var, '\n'.join(current_lines)))

        # Build merged preamble
        merged = []
        processed_vars = set()

        # First pass: preserve structure from GitHub, but use local values where they exist
        for line_type, var_name, line in github_lines:
            if line_type == 'var':
                if var_name in local_vars:
                    # Use local customized value
                    merged.append(local_vars[var_name])
                else:
                    # New variable from GitHub - use default
                    merged.append(line)
                processed_vars.add(var_name)
            else:
                # Comments, blank lines, etc. - preserve from GitHub
                merged.append(line)

        # Second pass: add any local-only variables (not in GitHub) at the end
        local_only_vars = []
        for var_name, line in local_vars.items():
            if var_name not in processed_vars:
                local_only_vars.append(line)

        if local_only_vars:
            # Add a comment and the local-only variables
            merged.append('')
            merged.append('{} User-added variables (not in template):'.format(comment_char))
            merged.extend(local_only_vars)

        return '\n'.join(merged)

    def do_update(self, new_pckg):
        # Update the content in the system
        # If using demarcation, preserve anything above it (the "preamble").
        preamble = None
        demarcation_line = None
        new_body = new_pckg.body

        if Pckgd.do_not_edit_demarcation in self.body and self.headers['Editable'] == True:
            # Find the actual demarcation line to preserve it exactly
            for line in self.body.split('\n'):
                if Pckgd.do_not_edit_demarcation in line:
                    demarcation_line = line
                    # Split on the full line, not just the pattern
                    parts = self.body.split(line, 1)
                    if len(parts) > 0:
                        preamble = parts[0].rstrip('\n')
                    break

        # Assemble new body with old preamble.
        if preamble is not None and Pckgd.do_not_edit_demarcation in new_pckg.body and new_pckg.headers['Editable'] == True:
            # Find GitHub's demarcation line
            github_demarcation_line = None
            github_preamble = None
            new_body_content = None

            for line in new_pckg.body.split('\n'):
                if Pckgd.do_not_edit_demarcation in line:
                    github_demarcation_line = line
                    # Split on the full line
                    parts = new_pckg.body.split(line, 1)
                    if len(parts) > 0:
                        github_preamble = parts[0].rstrip('\n')
                    if len(parts) > 1:
                        new_body_content = parts[1].lstrip('\n')
                    break

            # Use GitHub's demarcation line if we don't have one
            if not demarcation_line and github_demarcation_line:
                demarcation_line = github_demarcation_line

            # Merge variable sections intelligently
            if github_preamble:
                try:
                    merged_preamble = Pckgd._merge_variables(preamble, github_preamble, self.typeId)
                except Exception as e:
                    # If merge fails, fall back to preserving local preamble
                    model.DebugPrint("Warning: Variable merge failed for {0}: {1}".format(self.filename, str(e)))
                    merged_preamble = preamble
            else:
                merged_preamble = preamble

            # Assemble final body with preserved demarcation line
            if demarcation_line and new_body_content is not None:
                new_body = merged_preamble + '\n' + demarcation_line + '\n' + new_body_content
            else:
                # Fallback if parsing failed
                new_body = merged_preamble + '\n' + ('#' if self.typeId == 5 else '--') + ' ' + Pckgd.do_not_edit_demarcation + '\n' + new_pckg.body
        elif preamble is not None:
            # GitHub doesn't have demarcation but local does - preserve local preamble
            if demarcation_line:
                new_body = preamble + '\n' + demarcation_line + '\n' + new_pckg.body
            else:
                new_body = preamble + '\n' + ('#' if self.typeId == 5 else '--') + ' ' + Pckgd.do_not_edit_demarcation + '\n' + new_pckg.body

        v = new_pckg.version

        self.body = new_body

        if "Version" in self.headers or "Version" in new_pckg.headers:
            new_body = Pckgd.set_header(new_body, 'Version', v, self.typeId)

        if self.typeId == 5:
            model.WriteContentPython(self.filename, new_body)
        elif self.typeId == 4:
            model.WriteContentSql(self.filename, new_body)

        # TODO update dependencies, as well.



def do_listing_view():
    model.Header = "Package Manager"
    model.Title = "Package Manager"

    print("<h2>Installed Packages</h2>\n")
    print("<div class=\"section row\">\n")

    installed = Pckgd.find_installed_packages()
    if (not installed) or (len(installed) == 0):
        print("<p>No packages are currently installed.<p />\n")

    # sort by name
    installed.sort(key=lambda p: p.name().lower())

    for p in installed:
        if p.has_dependents():
            continue  # skip packages that have dependents; they will be shown with their parent package.

        print("<div class=\"package col-12 col-sm-6 col-md-4 col-lg-3\">\n")
        print("<div class=\"package-header\" style=\"{}\"></div>\n".format(p.get_header_style()))

        print("<div class=\"package-body\">\n")
        print("<h3>{}</h3>\n".format(p.name()))
        if 'Description' in p.headers:
            print("<p>{}</p>\n".format(p.headers['Description']))

        update = False
        try:
            update = p.has_update_available()
        except Exception as e:
            print("<p><strong>Error checking for updates: {}</strong></p>\n".format(str(e)))

        update_dep = False
        try:
            update_dep = p.dependencies_with_updates_available()
        except Exception as e:
            print("<p><strong>Error checking for dependency updates: {}</strong></p>\n".format(str(e)))

        if update or update_dep:
            print("<p><strong style=\"color:#600\">Update available.</strong></p>\n")

        pkg_caps = []
        if 'Author' in p.headers:
            pkg_caps.append("by&nbsp;{}".format(p.headers['Author']))

        if 'License' in p.headers:
            pkg_caps.append("<span title=\"License\">{}</span>".format(p.headers['License']))

        pkg_caps.append("Version:&nbsp;{}".format(p.headers['Version']))

        if len(update_dep) > 0:
            pkg_caps.append("<span style=\"color:#600\" title=\"{0} files are ready to be updated.\">&#x21bb;&nbsp;{0} Files</span>".format(1 * (not not update) + len(update_dep)))

        elif update:
            pkg_caps.append("<span style=\"color:#600\" title=\"New Version Available\">&#x21bb;&nbsp;{}</span>".format(update))

        if p.has_dependencies() or p.has_dependents():
            pkg_caps.append("<span title=\"{0} Dependents: files that depend on this file\">{0}</span>:<span title=\"{1} Dependencies: files on which this file depends\">{1}</span>".format(p.has_dependents(), p.has_dependencies()))

        print("<p class=\"package-caption\">{}</p>\n".format(" &bull; ".join(pkg_caps)))

        print(p.get_action_buttons())

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
                  height: 14em;
                  margin-bottom: 2em;
                  overflow-y: auto;
                  overflow-x: hidden;
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

def do_update_view():
    model.Header = "Package Manager - Update Package"
    model.Title = "Package Manager - Update Package"

    pkg_name = Data.pkg
    pkg = None
    for p in Pckgd.find_installed_packages():
        if p.filename_with_extension() == pkg_name:
            pkg = p
            break

    if not pkg:
        print("<p><strong>Package not found: {}</strong></p>\n".format(pkg_name))
        return

    print("<h2>Update Package: {}</h2>\n".format(pkg.name()))

    update_source = pkg.get_update_source()
    if not update_source:
        print("<p><strong>No update source defined for this package.</strong></p>\n")
        return

    remote_content = model.RestGet(update_source, {})
    if remote_content == "404: Not Found":
        print("<p><strong>Update source not found: {}</strong></p>\n".format(update_source))
        return

    remote_pkg = Pckgd(pkg.typeId, pkg.filename, remote_content)

    if remote_pkg.version == pkg.version:
        print("<p><strong>This package is already up to date.</strong></p>\n")
        return

    # Perform the update
    try:
        pkg.do_update(remote_pkg)
        print("<p><strong>Package updated successfully to version {}.</strong></p>\n".format(remote_pkg.version))
    except Exception as e:
        print("<p><strong>Error updating package: {}</strong></p>\n".format(str(e)))


if model.HttpMethod == "get" and Data.v == "":
    do_listing_view()


elif model.HttpMethod == "get" and Data.v == "update" and Data.pkg != "":
    do_update_view()



