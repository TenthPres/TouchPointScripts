# Pckgd
# Title: Atrium Sync
# Description: Keep Atrium users and their access levels in line with TouchPoint searches and status flags.
# Updates from: GitHub/TenthPres/TouchPointScripts/AtriumControl/AtriumSync.py
# Depends on: AtriumLib.py
# Version: 0.2.0
# License: AGPL-3.0
# Author: James at Tenth
# Editable: False

# Do not make edits to this file.  They will be overwritten during updates.

# Configuration lives in Special Content as AtriumConfig.json.  Each linked person carries their Atrium user's GUID in a
# text Extra Value (default name "AtriumGuid"), which is the only link between the two systems.  See README.md.
#
# Rules of engagement, because this changes who can open doors:
#  - It only ever touches Atrium users linked through the Extra Value.  Everyone else in Atrium is left alone.
#  - Access levels that no rule mentions are left alone on linked users.
#  - It never deletes anything.  People who stop qualifying lose their managed levels and are optionally disabled.
#  - Nothing is written unless "dryRun" is false, and no run may make more than "changeLimit" changes.

global model, Data, q

import json

try:
    exec(model.PythonContent("AtriumLib").replace("\r\n", "\n").replace("\r", "\n"), globals())
except NameError:  # running under test, where AtriumLib is imported normally
    from AtriumLib import *  # noqa

DEFAULT_CONFIG = {
    "dryRun": True,
    "changeLimit": 25,
    "guidExtraValue": "AtriumGuid",
    "linkByName": False,  # adopt an existing, unlinked Atrium user when exactly one has the same first and last name
    "syncNames": True,
    "disableWhenNoAccess": True,
    "allowEmptyRun": False,  # a run where nobody qualifies is almost always a broken search, so refuse unless allowed
    "rules": [],  # [{"name": "Staff", "accessLevel": "Staff", "search": "StatusFlag = 'F10'"}]
}


# ---------------------------------------------------------------------------------------------------------------------
# Planning (pure; no TouchPoint or network calls)
# ---------------------------------------------------------------------------------------------------------------------

def name_key(first, last):
    return (ascii_name(first).lower(), ascii_name(last).lower())


def plan_sync(qualified, users, links, managed_levels, options):
    """
    qualified:      {peopleId(int): {"first": str, "last": str, "levels": [accessLevelId, ...]}}
    users:          list of parse_user() dicts from Atrium
    links:          {peopleId(int): guid} as read from the Extra Value
    managed_levels: set of access level ids that rules control
    returns (actions, warnings)

    Actions are dicts with a "kind" of: create, link, update.  "update" carries only the changed fields.  The GUID,
    not the numeric Atrium id, is the link, because ids can be reused after a delete.
    """
    actions, warnings = [], []
    by_guid = dict((u["guid"], u) for u in users)

    holders = {}
    for pid, guid in links.items():
        holders.setdefault(guid, []).append(pid)
    blocked = set()
    for guid, pids in holders.items():
        if len(pids) > 1:
            warnings.append("People {} all claim the same Atrium user; leaving all of them alone until fixed."
                            .format(sorted(pids)))
            blocked.update(pids)

    live_links = {}
    for pid, guid in links.items():
        if pid in blocked:
            continue
        u = by_guid.get(guid)
        if u is None:
            warnings.append("Person {} has an Atrium GUID that no longer exists; treating them as unlinked.".format(pid))
            continue
        live_links[pid] = u
    claimed = set(g for g in holders if g in by_guid)  # an Atrium user someone claims is never adopted by name

    if not qualified and live_links and not options.get("allowEmptyRun"):
        warnings.append("Nobody qualifies for any rule but {} people are linked.  Refusing to revoke everything; "
                        "check the searches (or set allowEmptyRun).".format(len(live_links)))
        return actions, warnings

    unlinked_by_name = {}
    for u in users:
        if u["guid"] not in claimed:
            unlinked_by_name.setdefault(name_key(u["first_name"], u["last_name"]), []).append(u)

    for pid in sorted(qualified):
        if pid in blocked:
            continue
        want = qualified[pid]
        u = live_links.get(pid)

        if u is None:
            candidates = unlinked_by_name.get(name_key(want["first"], want["last"]), [])
            if candidates and not options.get("linkByName"):
                warnings.append("Person {} has the same name as an existing, unlinked Atrium user; not creating a "
                                "duplicate.  Link them (linkByName) or resolve by hand.".format(pid))
                continue
            if len(candidates) > 1:
                warnings.append("Person {} matches {} unlinked Atrium users by name; skipping.".format(pid, len(candidates)))
                continue
            if len(candidates) == 1:
                u = candidates[0]
                unlinked_by_name[name_key(want["first"], want["last"])] = []
                actions.append({"kind": "link", "peopleId": pid, "guid": u["guid"]})
            else:
                levels = _unique(want["levels"])
                if len(levels) > ACCESS_LEVEL_SLOTS:
                    warnings.append("Person {} qualifies for {} access levels; Atrium holds {}.  Truncated."
                                    .format(pid, len(levels), ACCESS_LEVEL_SLOTS))
                    levels = levels[:ACCESS_LEVEL_SLOTS]
                actions.append({"kind": "create", "peopleId": pid, "first": ascii_name(want["first"]),
                                "last": ascii_name(want["last"]), "levels": levels})
                continue

        changes = {}
        keep = [l for l in u["access_levels"] if l not in managed_levels]
        new_levels = keep + [l for l in _unique(want["levels"]) if l not in keep]
        if len(new_levels) > ACCESS_LEVEL_SLOTS:
            warnings.append("Person {} would need {} access levels; Atrium holds {}.  Truncated."
                            .format(pid, len(new_levels), ACCESS_LEVEL_SLOTS))
            new_levels = new_levels[:ACCESS_LEVEL_SLOTS]
        if sorted(new_levels) != sorted(u["access_levels"]):
            changes["access_levels"] = new_levels
        if options.get("syncNames") and name_key(u["first_name"], u["last_name"]) != name_key(want["first"], want["last"]):
            changes["first_name"] = ascii_name(want["first"])
            changes["last_name"] = ascii_name(want["last"])
        if not u["enabled"]:
            changes["enabled"] = True
        if changes:
            actions.append({"kind": "update", "peopleId": pid, "userId": u["id"], "changes": changes})

    for pid, u in sorted(live_links.items()):
        if pid in qualified:
            continue
        keep = [l for l in u["access_levels"] if l not in managed_levels]
        changes = {}
        if keep != u["access_levels"]:
            changes["access_levels"] = keep
        if options.get("disableWhenNoAccess") and not keep and u["enabled"]:
            changes["enabled"] = False
        if changes:
            actions.append({"kind": "update", "peopleId": pid, "userId": u["id"], "changes": changes})

    return actions, warnings


def _unique(items):
    seen, out = set(), []
    for i in items:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def apply_actions(client, actions, set_link):
    """
    Executes the plan.  `set_link(peopleId, guid)` records the link (the Extra Value).  A created user's link is
    recorded immediately, so a later failure can't leave an orphan that the next run would duplicate.
    Returns a list of (action, error-or-None).
    """
    results = []
    for a in actions:
        try:
            if a["kind"] == "link":
                set_link(a["peopleId"], a["guid"])
            elif a["kind"] == "create":
                new_id = client.add_user(a["first"], a["last"], access_levels=a["levels"])
                set_link(a["peopleId"], client.get_user(new_id)["guid"])
            elif a["kind"] == "update":
                client.update_user(a["userId"], **a["changes"])
            results.append((a, None))
        except Exception as e:  # keep going; one bad record shouldn't strand the rest
            results.append((a, str(e)))
    return results


def count_writes(actions):
    return len([a for a in actions if a["kind"] in ("create", "update")])


# ---------------------------------------------------------------------------------------------------------------------
# TouchPoint glue
# ---------------------------------------------------------------------------------------------------------------------

def load_json(name, default):
    raw = model.TextContent(name)
    return json.loads(raw) if raw else default


def resolve_level(spec, levels_by_label):
    if isinstance(spec, int) or str(spec).isdigit():
        return int(spec)
    found = levels_by_label.get(str(spec).strip().lower())
    if found is None:
        raise AtriumError("No Atrium access level named '{}'".format(spec))
    return found


def people_names(pids):
    names = {}
    pids = list(pids)
    for i in range(0, len(pids), 400):
        chunk = pids[i:i + 400]
        for r in q.QuerySql(
                "SELECT PeopleId, COALESCE(NULLIF(NickName, ''), FirstName) AS First, LastName AS Last "
                "FROM People WHERE PeopleId IN ({})".format(",".join(str(int(p)) for p in chunk))):
            names[int(r.PeopleId)] = (r.First or "", r.Last or "")
    return names


def run():
    config = dict(DEFAULT_CONFIG)
    config.update(load_json("AtriumConfig.json", {}))
    ev = config["guidExtraValue"]

    client = AtriumClient(model.Setting("AtriumApiUrl", ""), model.Setting("AtriumApiUser", ""),
                          model.Setting("AtriumApiPassword", ""), touchpoint_transport(model))
    levels_by_label = dict((l["label"].strip().lower(), l["id"]) for l in client.list_access_levels())

    qualified, managed = {}, set()
    for rule in config["rules"]:
        level = resolve_level(rule["accessLevel"], levels_by_label)
        managed.add(level)
        for p in q.QueryList(rule["search"]):
            entry = qualified.setdefault(int(p.PeopleId), {"levels": []})
            entry["levels"].append(level)
    names = people_names(qualified.keys())
    for pid in list(qualified):
        if pid not in names:
            del qualified[pid]
            continue
        qualified[pid]["first"], qualified[pid]["last"] = names[pid]

    links = dict((int(r.PeopleId), r.Data) for r in q.QuerySql(
        "SELECT PeopleId, Data FROM PeopleExtra WHERE Field = '{}' AND Data IS NOT NULL AND Data <> ''"
        .format(ev.replace("'", "''"))))

    actions, warnings = plan_sync(qualified, client.list_users(), links, managed, config)
    writes = count_writes(actions)

    print("<h3>Atrium Sync{}</h3>".format(" (dry run)" if config["dryRun"] else ""))
    for w in warnings:
        print("<p><b>Warning:</b> {}</p>".format(w))
    print("<p>{} qualifying people, {} planned actions ({} Atrium writes).</p>".format(len(qualified), len(actions), writes))
    for a in actions:
        print("<div>{}</div>".format(json.dumps(a)))

    if config["dryRun"]:
        return
    if writes > config["changeLimit"]:
        print("<p><b>Not applied:</b> {} writes exceeds changeLimit of {}.  Review the plan, then raise the limit or "
              "run again after correcting the cause.</p>".format(writes, config["changeLimit"]))
        return

    def set_link(pid, guid):
        model.AddExtraValueText(pid, ev, guid)

    for a, err in apply_actions(client, actions, set_link):
        if err:
            print("<p><b>Failed:</b> {} &mdash; {}</p>".format(json.dumps(a), err))


if "model" in globals() and hasattr(model, "TextContent"):
    run()
