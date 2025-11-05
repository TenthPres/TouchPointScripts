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

    do_not_edit_demarcation = "PCKGD_MANAGED_SECTION"
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
            <a href="/PyScript/Pckgd?v=update&pkg={}&show_diff=true" class="btn btn-primary">Update</a>
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
                source_meta = Pckgd._get_source_repo_metadata(path[1] + "/" + path[2])

                default_branch = "main"
                if 'default_branch' in source_meta:
                    default_branch = source_meta['default_branch']

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
                source_meta = Pckgd._get_source_repo_metadata(path[1] + "/" + path[2])

                default_branch = "main"
                if 'default_branch' in source_meta:
                    default_branch = source_meta['default_branch']

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
            if remote_content == "404: Not Found":  # How source repositories (e.g., GitHub) handle 404s
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
    def _get_source_repo_metadata(repo_path, bypass_cache=False):
        """Get metadata for a source repository (e.g., GitHub)"""
        meta = Pckgd._get_saved_meta()

        if not "source_repo_meta" in meta:
            meta["source_repo_meta"] = {}

        if not repo_path in meta["source_repo_meta"]:
            meta["source_repo_meta"][repo_path] = {}

        if '_expires' not in meta["source_repo_meta"][repo_path] or meta["source_repo_meta"][repo_path]['_expires'] < time.time() or bypass_cache:
            # Query GitHub API to get default branch and other metadata
            url = "https://api.github.com/repos/{}".format(repo_path)
            response = model.RestGet(url, {"Accept": "application/vnd.github.v3+json"})
            meta["source_repo_meta"][repo_path]['data'] = json.loads(response)
            meta["source_repo_meta"][repo_path]['_expires'] = time.time() + 86400  # cache for 1 day
            meta['_dirty'] = True

        return meta["source_repo_meta"][repo_path]['data']

    @staticmethod
    def _save_meta_if_dirty():
        meta = Pckgd._get_saved_meta()
        if '_dirty' in meta and meta['_dirty']:
            del meta['_dirty']
            model.WriteContentText("PckgdCache.json", json.dumps(meta, indent=2))


    @staticmethod
    def _merge_variables(local_preamble, source_preamble, type_id):
        """
        Intelligently merge variable sections using difflib:
        - Uses three-way merge logic
        - Detects what changed between local and source
        - Automatically resolves non-conflicting changes
        - Preserves user customizations
        - Adds new variables from source
        """
        import difflib
        import re

        comment_char = '#' if type_id == 5 else '--'

        # Helper to separate headers from variables
        def split_headers_and_vars(preamble):
            """Split preamble into headers and configuration variables"""
            lines = preamble.split('\n')
            headers = []
            config = []
            in_config = False
            var_pattern = r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)$'

            for line in lines:
                stripped = line.strip()

                # Check if we're entering the config section
                if not in_config and 'CONFIGURATION' in line and line.strip().startswith(comment_char):
                    # This is the config section header
                    in_config = True
                    config.append(line)
                    continue

                # Check if this line is a variable assignment (actual code, not comment)
                is_variable = False
                if stripped and not stripped.startswith(comment_char):
                    # Check if it matches variable pattern
                    if re.match(var_pattern, stripped):
                        is_variable = True
                        in_config = True

                if is_variable or in_config:
                    # We're in or starting the config section
                    config.append(line)
                else:
                    # Still in headers
                    headers.append(line)

            return '\n'.join(headers), '\n'.join(config)

        # Parse variable assignments (simple but robust)
        def parse_variables(code):
            """Extract variable assignments as {var_name: full_assignment_text}"""
            var_pattern = r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)$'
            variables = {}
            lines = code.split('\n')
            current_var = None
            current_lines = []

            for line in lines:
                stripped = line.strip()

                # Skip empty lines and comments
                if not stripped or stripped.startswith(comment_char):
                    # If we were tracking a multi-line, this ends it
                    if current_var:
                        variables[current_var] = '\n'.join(current_lines)
                        current_var = None
                        current_lines = []
                    continue

                # Check if this is a variable assignment
                match = re.match(var_pattern, stripped)
                if match:
                    # Save previous variable if any
                    if current_var:
                        variables[current_var] = '\n'.join(current_lines)

                    current_var = match.group(1)
                    current_lines = [line]

                    # Check for unclosed brackets/parens (multi-line)
                    value = match.group(2)
                    open_count = value.count('(') + value.count('[') + value.count('{')
                    close_count = value.count(')') + value.count(']') + value.count('}')

                    if open_count == close_count and not value.endswith('\\'):
                        # Single line assignment
                        variables[current_var] = line
                        current_var = None
                        current_lines = []
                elif current_var:
                    # Continuation of multi-line assignment
                    current_lines.append(line)

                    # Check if we're closing the assignment
                    if ')' in line or ']' in line or '}' in line:
                        # Count brackets to see if balanced
                        full_text = '\n'.join(current_lines)
                        open_count = full_text.count('(') + full_text.count('[') + full_text.count('{')
                        close_count = full_text.count(')') + full_text.count(']') + full_text.count('}')

                        if open_count == close_count:
                            variables[current_var] = full_text
                            current_var = None
                            current_lines = []

            # Save last variable if any
            if current_var:
                variables[current_var] = '\n'.join(current_lines)

            return variables

        def get_structure(code):
            """Get code structure preserving comments and order"""
            lines = code.split('\n')
            structure = []
            var_pattern = r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)$'
            in_var = None

            for line in lines:
                stripped = line.strip()

                # Check if this is a variable assignment (not a comment)
                match = re.match(var_pattern, stripped) if stripped and not stripped.startswith(comment_char) else None

                if match:
                    if in_var:
                        structure.append(('var_end', in_var))
                    in_var = match.group(1)
                    structure.append(('var_start', in_var, line))
                elif in_var and stripped and not stripped.startswith(comment_char):
                    # Continuation of multi-line assignment
                    structure.append(('var_continue', in_var, line))
                    if ')' in line or ']' in line or '}' in line:
                        # Might be end of multi-line
                        in_var = None
                else:
                    # Comments, blank lines, etc.
                    if in_var:
                        structure.append(('var_end', in_var))
                        in_var = None
                    structure.append(('text', None, line))

            return structure

        # Separate headers from configuration variables
        local_headers, local_config = split_headers_and_vars(local_preamble)
        source_headers, source_config = split_headers_and_vars(source_preamble)

        # If local has config section but source doesn't, we need to be smarter
        # Source might have variables but not the CONFIGURATION header yet
        if local_config and not source_config:
            # Check if source has any variables at all
            source_has_vars = False
            for line in source_preamble.split('\n'):
                stripped = line.strip()
                if stripped and not stripped.startswith(comment_char):
                    import re
                    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*=', stripped):
                        source_has_vars = True
                        break

            if source_has_vars:
                # Source has variables but no CONFIGURATION section
                # Split source differently - everything after Editable is config
                lines = source_preamble.split('\n')
                header_lines = []
                config_lines = []
                found_editable = False

                for line in lines:
                    if 'Editable:' in line:
                        header_lines.append(line)
                        found_editable = True
                    elif found_editable:
                        config_lines.append(line)
                    else:
                        header_lines.append(line)

                source_headers = '\n'.join(header_lines)
                source_config = '\n'.join(config_lines)

        # DEBUG: Log the configs before parsing
        try:
            model.DebugPrint("=== CONFIG SECTIONS ===")
            model.DebugPrint("Local config length: " + str(len(local_config)))
            model.DebugPrint("Source config length: " + str(len(source_config)))
            model.DebugPrint("Local config first 500 chars:\n" + local_config[:500])
            model.DebugPrint("Source config first 500 chars:\n" + source_config[:500])
        except Exception as ex:
            model.DebugPrint("DEBUG ERROR: " + str(ex))

        # Parse only the configuration sections
        local_vars = parse_variables(local_config)
        source_vars = parse_variables(source_config)

        # DEBUG: Log what we parsed
        try:
            model.DebugPrint("=== MERGE DEBUG ===")
            model.DebugPrint("Local vars: " + str(local_vars.keys()))
            model.DebugPrint("Source vars: " + str(source_vars.keys()))
            if 'AZURE_ACCOUNT_KEY' in local_vars:
                model.DebugPrint("Local AZURE_ACCOUNT_KEY: " + local_vars['AZURE_ACCOUNT_KEY'][:50])
            if 'AZURE_ACCOUNT_KEY' in source_vars:
                model.DebugPrint("Source AZURE_ACCOUNT_KEY: " + source_vars['AZURE_ACCOUNT_KEY'][:50])
        except Exception as ex:
            model.DebugPrint("DEBUG ERROR: " + str(ex))

        # Compute differences using difflib
        local_var_names = set(local_vars.keys())
        source_var_names = set(source_vars.keys())

        # Variables only in local (user added)
        local_only = local_var_names - source_var_names

        # Variables only in source (new from update)
        source_only = source_var_names - local_var_names

        # Variables in both (potential conflicts or unchanged)
        both = local_var_names & source_var_names

        # Check for conflicts (both changed same variable)
        conflicts = []
        for var in both:
            if local_vars[var] != source_vars[var]:
                # Variable exists in both but values differ
                # This is where user customized it - keep user's version
                conflicts.append(var)

        # Build merged result
        merged_lines = []
        processed = set()

        # Start with source headers (updated version, etc.)
        if source_headers:
            merged_lines.append(source_headers)

        # Add a blank line between headers and config
        if source_headers and (local_config or source_config):
            merged_lines.append('')

        # Use local config structure to preserve comments and formatting
        # This includes the # ========== CONFIGURATION ========== header
        if local_config:
            local_structure = get_structure(local_config)
            current_var_lines = []
            current_var = None

            # Track the closing marker position (# =========)
            closing_marker_index = None
            temp_merged_lines = []

            for idx, item in enumerate(local_structure):
                if item[0] == 'var_start':
                    var_name = item[1]
                    current_var = var_name
                    current_var_lines = []

                    # Always use local version if it exists
                    if var_name in local_vars:
                        temp_merged_lines.append(local_vars[var_name])
                        processed.add(var_name)
                        current_var = None
                    else:
                        # Shouldn't happen since we're iterating local structure
                        current_var_lines.append(item[2])
                elif item[0] == 'var_continue' and current_var:
                    current_var_lines.append(item[2])
                elif item[0] == 'var_end' or (item[0] == 'text' and current_var):
                    if current_var and current_var_lines:
                        temp_merged_lines.append('\n'.join(current_var_lines))
                        processed.add(current_var)
                    current_var = None
                    current_var_lines = []

                    if item[0] == 'text':
                        # Check if this is the closing marker line
                        line = item[2]
                        if line.strip().startswith(comment_char) and '========' in line and len(line.strip()) < 20:
                            closing_marker_index = len(temp_merged_lines)
                        # Preserve comments and blank lines from local
                        temp_merged_lines.append(line)
                else:
                    # Preserve all text (comments, blank lines, etc.) from local
                    line = item[2]
                    if line.strip().startswith(comment_char) and '========' in line and len(line.strip()) < 20:
                        closing_marker_index = len(temp_merged_lines)
                    temp_merged_lines.append(line)

            # Add remaining current var if any
            if current_var and current_var_lines:
                temp_merged_lines.append('\n'.join(current_var_lines))
                processed.add(current_var)

            # Add new variables from source - insert before closing marker if found
            source_only_vars = source_var_names - local_var_names
            if source_only_vars:
                new_var_lines = []
                for var in sorted(source_only_vars):
                    new_var_lines.append(source_vars[var])

                # Insert new variables before the closing marker, or at the end
                if closing_marker_index is not None:
                    # Insert before closing marker
                    merged_lines.extend(temp_merged_lines[:closing_marker_index])
                    merged_lines.append('')  # Blank line before new vars
                    merged_lines.extend(new_var_lines)
                    merged_lines.extend(temp_merged_lines[closing_marker_index:])
                else:
                    # No closing marker, add at end
                    merged_lines.extend(temp_merged_lines)
                    merged_lines.append('')
                    merged_lines.extend(new_var_lines)
            else:
                # No new variables, use temp lines as-is
                merged_lines.extend(temp_merged_lines)
        elif source_config:
            # No local config exists, use source config entirely
            merged_lines.append(source_config)

        # Add user-only variables at the end
        if local_only:
            merged_lines.append('')
            merged_lines.append('{} User-added variables (not in source):'.format(comment_char))
            for var in sorted(local_only):
                merged_lines.append(local_vars[var])

        result = '\n'.join(merged_lines)

        # DEBUG: Log the result
        try:
            model.DebugPrint("=== MERGE RESULT ===")
            model.DebugPrint("Result length: " + str(len(result)))
            model.DebugPrint("First 500 chars: " + result[:500])
        except:
            pass

        return result

    @staticmethod
    def generate_diff_html(local_text, source_text, context_lines=3):
        """Generate side-by-side HTML diff view using difflib"""
        import difflib

        local_lines = local_text.splitlines()
        source_lines = source_text.splitlines()

        # Use SequenceMatcher for side-by-side comparison
        matcher = difflib.SequenceMatcher(None, local_lines, source_lines)

        html_lines = ['<div class="diff-view">']
        html_lines.append('<table class="diff-table">')
        html_lines.append('<thead><tr>')
        html_lines.append('<th class="line-num">Line</th>')
        html_lines.append('<th class="diff-column">Your Current Version</th>')
        html_lines.append('<th class="line-num">Line</th>')
        html_lines.append('<th class="diff-column">After Update</th>')
        html_lines.append('</tr></thead>')
        html_lines.append('<tbody>')

        local_line_num = 1
        source_line_num = 1

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Show context lines - if context_lines is large enough, show everything
                num_equal_lines = i2 - i1

                if context_lines >= num_equal_lines or context_lines >= 50:
                    # Show all equal lines (for config sections or when context is large)
                    for i in range(i1, i2):
                        j = j1 + (i - i1)
                        html_lines.append('<tr class="diff-unchanged">')
                        html_lines.append('<td class="line-num">{}</td>'.format(local_line_num))
                        html_lines.append('<td class="diff-line">{}</td>'.format(
                            local_lines[i].replace('<', '&lt;').replace('>', '&gt;')
                        ))
                        html_lines.append('<td class="line-num">{}</td>'.format(source_line_num))
                        html_lines.append('<td class="diff-line">{}</td>'.format(
                            source_lines[j].replace('<', '&lt;').replace('>', '&gt;')
                        ))
                        html_lines.append('</tr>')
                        local_line_num += 1
                        source_line_num += 1
                else:
                    # Show limited context with ellipsis for large unchanged sections
                    # Show first few lines
                    for i in range(i1, min(i1 + context_lines, i2)):
                        j = j1 + (i - i1)
                        html_lines.append('<tr class="diff-unchanged">')
                        html_lines.append('<td class="line-num">{}</td>'.format(local_line_num))
                        html_lines.append('<td class="diff-line">{}</td>'.format(
                            local_lines[i].replace('<', '&lt;').replace('>', '&gt;')
                        ))
                        html_lines.append('<td class="line-num">{}</td>'.format(source_line_num))
                        html_lines.append('<td class="diff-line">{}</td>'.format(
                            source_lines[j].replace('<', '&lt;').replace('>', '&gt;')
                        ))
                        html_lines.append('</tr>')
                        local_line_num += 1
                        source_line_num += 1

                    # Show ellipsis if we skipped lines
                    if i2 - i1 > context_lines * 2:
                        lines_skipped = (i2 - i1) - (context_lines * 2)
                        html_lines.append('<tr class="diff-ellipsis">')
                        html_lines.append('<td class="line-num">...</td>')
                        html_lines.append('<td class="diff-line"><em>({} unchanged lines)</em></td>'.format(lines_skipped))
                        html_lines.append('<td class="line-num">...</td>')
                        html_lines.append('<td class="diff-line"><em>({} unchanged lines)</em></td>'.format(lines_skipped))
                        html_lines.append('</tr>')

                        # Update line numbers for skipped section
                        local_line_num += lines_skipped
                        source_line_num += lines_skipped

                        # Show last few lines
                        for i in range(max(i2 - context_lines, i1 + context_lines), i2):
                            j = j1 + (i - i1)
                            html_lines.append('<tr class="diff-unchanged">')
                            html_lines.append('<td class="line-num">{}</td>'.format(local_line_num))
                            html_lines.append('<td class="diff-line">{}</td>'.format(
                                local_lines[i].replace('<', '&lt;').replace('>', '&gt;')
                            ))
                            html_lines.append('<td class="line-num">{}</td>'.format(source_line_num))
                            html_lines.append('<td class="diff-line">{}</td>'.format(
                                source_lines[j].replace('<', '&lt;').replace('>', '&gt;')
                            ))
                            html_lines.append('</tr>')
                            local_line_num += 1
                            source_line_num += 1

            elif tag == 'delete':
                # Lines only in local (will be removed)
                for i in range(i1, i2):
                    html_lines.append('<tr class="diff-delete">')
                    html_lines.append('<td class="line-num">{}</td>'.format(local_line_num))
                    html_lines.append('<td class="diff-line diff-removed">{}</td>'.format(
                        local_lines[i].replace('<', '&lt;').replace('>', '&gt;')
                    ))
                    html_lines.append('<td class="line-num"></td>')
                    html_lines.append('<td class="diff-line"></td>')
                    html_lines.append('</tr>')
                    local_line_num += 1

            elif tag == 'insert':
                # Lines only in source (will be added)
                for j in range(j1, j2):
                    html_lines.append('<tr class="diff-insert">')
                    html_lines.append('<td class="line-num"></td>')
                    html_lines.append('<td class="diff-line"></td>')
                    html_lines.append('<td class="line-num">{}</td>'.format(source_line_num))
                    html_lines.append('<td class="diff-line diff-added">{}</td>'.format(
                        source_lines[j].replace('<', '&lt;').replace('>', '&gt;')
                    ))
                    html_lines.append('</tr>')
                    source_line_num += 1

            elif tag == 'replace':
                # Lines changed between versions
                max_lines = max(i2 - i1, j2 - j1)
                for k in range(max_lines):
                    i = i1 + k
                    j = j1 + k
                    html_lines.append('<tr class="diff-replace">')

                    if i < i2:
                        html_lines.append('<td class="line-num">{}</td>'.format(local_line_num))
                        html_lines.append('<td class="diff-line diff-changed">{}</td>'.format(
                            local_lines[i].replace('<', '&lt;').replace('>', '&gt;')
                        ))
                        local_line_num += 1
                    else:
                        html_lines.append('<td class="line-num"></td>')
                        html_lines.append('<td class="diff-line"></td>')

                    if j < j2:
                        html_lines.append('<td class="line-num">{}</td>'.format(source_line_num))
                        html_lines.append('<td class="diff-line diff-changed">{}</td>'.format(
                            source_lines[j].replace('<', '&lt;').replace('>', '&gt;')
                        ))
                        source_line_num += 1
                    else:
                        html_lines.append('<td class="line-num"></td>')
                        html_lines.append('<td class="diff-line"></td>')

                    html_lines.append('</tr>')

        html_lines.append('</tbody>')
        html_lines.append('</table>')
        html_lines.append('</div>')

        # Add CSS for side-by-side view
        html_lines.append('''
        <style>
            .diff-view {
                border: 1px solid #ddd;
                border-radius: 4px;
                margin: 10px 0;
                background: #fff;
                overflow-x: auto;
            }
            .diff-table {
                width: 100%;
                border-collapse: collapse;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
            }
            .diff-table thead {
                background: #f5f5f5;
                border-bottom: 2px solid #ddd;
            }
            .diff-table th {
                padding: 8px;
                text-align: left;
                font-weight: bold;
                border-right: 1px solid #ddd;
            }
            .diff-table th.line-num {
                width: 50px;
                text-align: right;
                background: #fafafa;
            }
            .diff-table th.diff-column {
                width: 45%;
            }
            .diff-table td {
                padding: 2px 8px;
                border-right: 1px solid #eee;
                vertical-align: top;
            }
            .line-num {
                color: #999;
                text-align: right;
                background: #fafafa;
                user-select: none;
                min-width: 40px;
            }
            .diff-line {
                white-space: pre;
                overflow-x: auto;
            }
            .diff-unchanged td {
                background: #fff;
            }
            .diff-delete td {
                background: #fff0f0;
            }
            .diff-insert td {
                background: #f0fff0;
            }
            .diff-replace td {
                background: #fffef0;
            }
            .diff-ellipsis td {
                background: #f9f9f9;
                color: #999;
                text-align: center;
                font-style: italic;
                padding: 8px;
            }
            .diff-removed {
                background: #ffcccc !important;
                color: #c00;
            }
            .diff-added {
                background: #ccffcc !important;
                color: #080;
            }
            .diff-changed {
                background: #ffffcc !important;
                color: #880;
            }
        </style>
        ''')

        return '\n'.join(html_lines)

    def generate_merged_body(self, new_pckg):
        """Generate the merged body without saving it (for preview)"""
        preamble = None
        demarcation_line = None
        new_body = new_pckg.body

        if Pckgd.do_not_edit_demarcation in self.body and self.headers['Editable'] == True:
            # Find the demarcation line that marks end of editable section
            comment_char = '#' if self.typeId == 5 else '--'

            for line in self.body.split('\n'):
                # Look for comment line containing our unique marker
                if Pckgd.do_not_edit_demarcation in line and line.strip().startswith(comment_char):
                    demarcation_line = line
                    # Split on the full line
                    parts = self.body.split(line, 1)
                    if len(parts) > 0:
                        preamble = parts[0].rstrip('\n')
                    break

        # Assemble new body with old preamble.
        if preamble is not None and Pckgd.do_not_edit_demarcation in new_pckg.body and new_pckg.headers['Editable'] == True:
            # Find source's demarcation line
            source_demarcation_line = None
            source_preamble = None
            new_body_content = None

            for line in new_pckg.body.split('\n'):
                # Look for comment line containing our unique marker
                if Pckgd.do_not_edit_demarcation in line and line.strip().startswith(comment_char):
                    source_demarcation_line = line
                    # Split on the full line
                    parts = new_pckg.body.split(line, 1)
                    if len(parts) > 0:
                        source_preamble = parts[0].rstrip('\n')
                    if len(parts) > 1:
                        new_body_content = parts[1].lstrip('\n')
                    break

            # Use source's demarcation line if we don't have one
            if not demarcation_line and source_demarcation_line:
                demarcation_line = source_demarcation_line

            # Merge variable sections intelligently
            if source_preamble:
                try:
                    merged_preamble = Pckgd._merge_variables(preamble, source_preamble, self.typeId)
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
            # Source doesn't have demarcation but local does - preserve local preamble
            if demarcation_line:
                new_body = preamble + '\n' + demarcation_line + '\n' + new_pckg.body
            else:
                new_body = preamble + '\n' + ('#' if self.typeId == 5 else '--') + ' ' + Pckgd.do_not_edit_demarcation + '\n' + new_pckg.body

        # Update version header
        v = new_pckg.version
        if "Version" in self.headers or "Version" in new_pckg.headers:
            new_body = Pckgd.set_header(new_body, 'Version', v, self.typeId)

        return new_body

    def do_update(self, new_pckg):
        """Apply the update and save to database"""
        new_body = self.generate_merged_body(new_pckg)

        self.body = new_body

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
    show_diff = hasattr(Data, 'show_diff') and Data.show_diff == 'true'
    confirm = hasattr(Data, 'confirm') and Data.confirm == 'true'

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

    # Show diff if requested
    if show_diff:
        print("<h3>Update Preview</h3>")
        print("<p>Current version: <strong>{}</strong> &rarr; New version: <strong>{}</strong></p>".format(
            pkg.version, remote_pkg.version
        ))

        # Action buttons at top
        print('<p style="margin: 15px 0;">')
        print('<a href="/PyScript/Pckgd?v=update&pkg={}&confirm=true" class="btn btn-primary">Confirm Update</a> '.format(pkg_name))
        print('<a href="/PyScript/Pckgd" class="btn btn-default">Cancel</a>')
        print('</p>')

        # Generate the merged result (what will actually be saved)
        merged_body = pkg.generate_merged_body(remote_pkg)

        # Show diff of configuration section if it exists
        if Pckgd.do_not_edit_demarcation in pkg.body:
            local_preamble = pkg.body.split(Pckgd.do_not_edit_demarcation)[0]
            if Pckgd.do_not_edit_demarcation in merged_body:
                merged_preamble = merged_body.split(Pckgd.do_not_edit_demarcation)[0]

                print("<h4>Configuration Changes:</h4>")
                print("<p><em>Your custom values will be preserved. New settings will be added if available.</em></p>")
                # Use large context to show all configuration lines
                print(Pckgd.generate_diff_html(local_preamble, merged_preamble, context_lines=1000))

        # Show full file diff in collapsible section
        print('<details style="margin-top: 20px;">')
        print('<summary style="cursor: pointer; font-size: 16px; font-weight: bold; padding: 10px; background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px;">')
        print('📄 Complete File Changes (click to expand)')
        print('</summary>')
        print('<div style="margin-top: 10px;">')
        print("<p><em>This shows all changes including code updates:</em></p>")
        # Use moderate context with ellipsis for very long unchanged sections
        print(Pckgd.generate_diff_html(pkg.body, merged_body, context_lines=5))
        print('</div>')
        print('</details>')
        return

    # Perform the update if confirmed
    if confirm or not show_diff:
        try:
            pkg.do_update(remote_pkg)
            print("<p><strong>Package updated successfully to version {}.</strong></p>\n".format(remote_pkg.version))
            print('<p><a href="/PyScript/Pckgd" class="btn btn-default">Back to Package Manager</a></p>')
        except Exception as e:
            print("<p><strong>Error updating package: {}</strong></p>\n".format(str(e)))
    else:
        # Default: show preview option
        print("<p>An update is available. Version <strong>{}</strong> &rarr; <strong>{}</strong></p>".format(
            pkg.version, remote_pkg.version
        ))
        print('<p><a href="/PyScript/Pckgd?v=update&pkg={}&show_diff=true" class="btn btn-info">Preview Changes</a>'.format(pkg_name))
        print('<a href="/PyScript/Pckgd?v=update&pkg={}&confirm=true" class="btn btn-primary">Update Now</a>'.format(pkg_name))
        print('<a href="/PyScript/Pckgd" class="btn btn-default">Cancel</a></p>')


if model.HttpMethod == "get" and Data.v == "":
    do_listing_view()


elif model.HttpMethod == "get" and Data.v == "update" and Data.pkg != "":
    do_update_view()
