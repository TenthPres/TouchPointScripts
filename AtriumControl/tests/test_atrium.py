"""
Offline tests for AtriumLib and the AtriumSync planner.  Run from AtriumControl/:  python -m unittest discover tests

Nothing here touches a controller.  A live read-only check lives in tools/atrium_probe.py.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import AtriumLib as L  # noqa: E402
import AtriumSync as S  # noqa: E402
import AtriumScheduleSync as SS  # noqa: E402
import datetime  # noqa: E402
import AtriumControl as AC  # noqa: E402


def user(uid, first, last, levels=(), enabled=True, guid=None):
    return {"id": uid, "guid": guid or "G{}".format(uid), "first_name": first, "last_name": last,
            "name": first + " " + last, "enabled": enabled, "activation": 0, "expiration": None,
            "access_levels": list(levels)}


OPTS = {"linkByName": False, "syncNames": True, "disableWhenNoAccess": True, "allowEmptyRun": False}


class CryptoTests(unittest.TestCase):
    def test_round_trip(self):
        key = "0123456789ABCDEF0123456789ABCDEF"
        body = "<SDK>café 'quoted' &amp;</SDK>".encode("ascii", "xmlcharrefreplace").decode("ascii")
        self.assertEqual(L.decrypt_body(key, L.encrypt_body(key, body)), body)

    def test_bad_checksum_is_rejected(self):
        key = "K" * 32
        enc = L.encrypt_body(key, "hello")
        self.assertIsNone(L.decrypt_body(key, enc[:-4] + "0000"))

    def test_plain_xml_passes_through(self):
        self.assertEqual(L.decrypt_body("k", "<a/>"), "<a/>")

    def test_known_vector(self):
        # RC4("Key", "Plaintext") from the published RC4 test vectors.
        self.assertEqual(L.rc4_hex("Key", "Plaintext"), "BBF316E8D940AF0AD3")


class RequestTests(unittest.TestCase):
    def test_read_request_matches_captured_format(self):
        xml = L.AtriumClient.build_request("REC", 7, [("cmd", "read"), ("sernum", "00009F90"), ("type", "user"),
                                                      ("id", 304), ("rec", "cfg")])
        self.assertEqual(xml, "<?xml version=\"1.0\" encoding=\"utf-8\"?><SDK xmlns='https://www.cdvi.ca/'><RECORDS>"
                              "<REC trans_id='7' cmd='read' sernum='00009F90' type='user' id='304' rec='cfg'></REC>"
                              "</RECORDS></SDK>")

    def test_values_are_escaped_and_ascii(self):
        xml = L.AtriumClient.build_request("REC", 1, [("cmd", "write")], [("label3", "O'Brien <&> é")])
        self.assertIn("label3='O&apos;Brien &lt;&amp;&gt; &#233;'", xml)
        xml.encode("ascii")

    def test_user_fields_only_includes_what_was_asked(self):
        self.assertEqual(L.user_fields(first_name="Ann"), {"label3": "Ann"})
        f = L.user_fields(access_levels=[7, 3])
        self.assertEqual([f["word24_{}".format(i)] for i in range(5)], [7, 3, 65535, 65535, 65535])
        self.assertNotIn("label3", f)

    def test_too_many_levels_refused(self):
        with self.assertRaises(L.AtriumError):
            L.user_fields(access_levels=[1, 2, 3, 4, 5, 6])

    def test_names_are_folded_to_ascii(self):
        self.assertEqual(L.ascii_name("José Muñoz"), "Jose Munoz")

    def test_parse_user(self):
        u = L.parse_user({"id": "9", "guid2": "AB", "label3": "A", "label4": "B", "valid": "1",
                          "utc_time22": "6AE7D280", "utc_time23": "FFFFFFFF", "word24_0": "7", "word24_1": "65535",
                          "word24_2": "3", "word24_3": "65535", "word24_4": "65535"})
        self.assertEqual((u["access_levels"], u["expiration"], u["enabled"]), ([7, 3], None, True))

    def test_dangerous_commands_need_confirmation(self):
        c = L.AtriumClient("http://x", "u", "p", transport=None)
        for call in (lambda: c.start_lockdown(), lambda: c.stop_lockdown(), lambda: c.momentary_unlock("S", 1, 5),
                     lambda: c.momentary_unlock("S", 1, 5, confirm="yes")):
            with self.assertRaises(L.AtriumError):
                call()

    def test_unlock_duration_is_bounded(self):
        c = L.AtriumClient("http://x", "u", "p", transport=None)
        for secs in (0, 301, -1):
            with self.assertRaises(L.AtriumError):
                c.momentary_unlock("S", 1, secs, confirm=True)

    def test_wireless_lock_flags(self):
        lock = L.parse_wireless_lock("S", 1, "NDE", {"byte0": "5", "byte1": "128", "bit5": "1"},
                                     {"bit1": "1", "bit2": "0", "bit5": "0"})
        self.assertTrue(lock["battery_low"] and lock["online"])
        self.assertFalse(lock["battery_critical"] or lock["rf_loss"])
        self.assertEqual(lock["volts"], 5.5)


class PlannerTests(unittest.TestCase):
    def q(self, pid, levels, first="Ann", last="Lee"):
        return {pid: {"first": first, "last": last, "levels": levels}}

    def test_new_person_is_created_with_levels(self):
        acts, warn = S.plan_sync(self.q(1, [7]), [], {}, {7}, OPTS)
        self.assertEqual([a["kind"] for a in acts], ["create"])
        self.assertEqual(acts[0]["levels"], [7])

    def test_unmanaged_levels_are_preserved(self):
        users = [user(10, "Ann", "Lee", levels=[3])]
        acts, _ = S.plan_sync(self.q(1, [7]), users, {1: "G10"}, {7}, OPTS)
        self.assertEqual(acts[0]["changes"]["access_levels"], [3, 7])

    def test_no_change_means_no_action(self):
        users = [user(10, "Ann", "Lee", levels=[7])]
        acts, _ = S.plan_sync(self.q(1, [7]), users, {1: "G10"}, {7}, OPTS)
        self.assertEqual(acts, [])

    def test_removed_person_loses_managed_levels_and_is_disabled(self):
        users = [user(10, "Ann", "Lee", levels=[3, 7]), user(11, "Bo", "Ray", levels=[7])]
        links = {1: "G10", 2: "G11"}
        acts, _ = S.plan_sync(self.q(2, [7], "Bo", "Ray"), users, links, {7}, OPTS)
        self.assertEqual(acts, [{"kind": "update", "peopleId": 1, "userId": 10, "changes": {"access_levels": [3]}}])

    def test_removed_person_with_nothing_left_is_disabled_not_deleted(self):
        users = [user(10, "Ann", "Lee", levels=[7]), user(11, "Bo", "Ray", levels=[7])]
        links = {1: "G10", 2: "G11"}
        acts, _ = S.plan_sync(self.q(2, [7], "Bo", "Ray"), users, links, {7}, OPTS)
        self.assertEqual(acts[0]["changes"], {"access_levels": [], "enabled": False})
        self.assertNotIn("delete", [a["kind"] for a in acts])

    def test_requalifying_person_is_re_enabled(self):
        users = [user(10, "Ann", "Lee", levels=[], enabled=False)]
        acts, _ = S.plan_sync(self.q(1, [7]), users, {1: "G10"}, {7}, OPTS)
        self.assertTrue(acts[0]["changes"]["enabled"])

    def test_unlinked_atrium_users_are_never_touched(self):
        users = [user(50, "Zed", "Zee", levels=[7])]
        acts, _ = S.plan_sync(self.q(1, [7]), users, {}, {7}, OPTS)
        self.assertEqual([a["kind"] for a in acts], ["create"])  # Zed untouched, Ann created

    def test_same_name_is_not_duplicated_unless_link_by_name(self):
        users = [user(50, "Ann", "Lee")]
        acts, warn = S.plan_sync(self.q(1, [7]), users, {}, {7}, OPTS)
        self.assertEqual(acts, [])
        self.assertTrue(warn)
        acts, _ = S.plan_sync(self.q(1, [7]), users, {}, {7}, dict(OPTS, linkByName=True))
        self.assertEqual([a["kind"] for a in acts], ["link", "update"])

    def test_ambiguous_name_is_skipped(self):
        users = [user(50, "Ann", "Lee"), user(51, "ann", "LEE")]
        acts, warn = S.plan_sync(self.q(1, [7]), users, {}, {7}, dict(OPTS, linkByName=True))
        self.assertEqual(acts, [])
        self.assertTrue(warn)

    def test_empty_run_refuses_to_revoke_everyone(self):
        users = [user(10, "Ann", "Lee", levels=[7])]
        acts, warn = S.plan_sync({}, users, {1: "G10"}, {7}, OPTS)
        self.assertEqual(acts, [])
        self.assertTrue(warn)

    def test_stale_link_is_dropped_and_not_trusted(self):
        users = [user(10, "Someone", "Else", guid="DIFFERENT")]
        acts, warn = S.plan_sync(self.q(1, [7]), users, {1: "G10"}, {7}, OPTS)
        self.assertEqual([a["kind"] for a in acts], ["create"])
        self.assertTrue(warn)

    def test_two_people_claiming_one_atrium_user_are_both_left_alone(self):
        users = [user(10, "Ann", "Lee", levels=[])]
        acts, warn = S.plan_sync({1: {"first": "Ann", "last": "Lee", "levels": [7]},
                                  2: {"first": "Ann", "last": "Lee", "levels": [7]}}, users, {1: "G10", 2: "G10"}, {7}, OPTS)
        self.assertEqual(acts, [])
        self.assertTrue(warn)

    def test_claimed_atrium_user_is_never_adopted_by_name(self):
        users = [user(10, "Ann", "Lee", levels=[7])]
        acts, _ = S.plan_sync({2: {"first": "Ann", "last": "Lee", "levels": [7]}}, users, {1: "G10"}, {7},
                              dict(OPTS, linkByName=True))
        # Person 2 gets a brand-new user rather than person 1's; person 1 (no longer qualifying) loses the level.
        self.assertEqual([(a["kind"], a["peopleId"]) for a in acts], [("create", 2), ("update", 1)])

    def test_more_than_five_levels_is_truncated_with_warning(self):
        acts, warn = S.plan_sync(self.q(1, [1, 2, 3, 4, 5, 6]), [], {}, set(range(1, 7)), OPTS)
        self.assertEqual(len(acts[0]["levels"]), 5)
        self.assertTrue(warn)

    def test_name_changes_sync(self):
        users = [user(10, "Ann", "Lee", levels=[7])]
        acts, _ = S.plan_sync(self.q(1, [7], "Anna", "Lee"), users, {1: "G10"}, {7}, OPTS)
        self.assertEqual(acts[0]["changes"], {"first_name": "Anna", "last_name": "Lee"})


class FakeClient(object):
    def __init__(self):
        self.calls = []

    def add_user(self, first, last, access_levels=()):
        self.calls.append(("add", first, last, list(access_levels)))
        return 99

    def get_user(self, uid):
        return {"guid": "NEWGUID"}

    def update_user(self, uid, **changes):
        self.calls.append(("update", uid, changes))
        if uid == 13:
            raise L.AtriumError("boom")


class ApplyTests(unittest.TestCase):
    def test_apply_records_links_and_survives_a_failure(self):
        links = {}
        acts = [{"kind": "create", "peopleId": 1, "first": "A", "last": "B", "levels": [7]},
                {"kind": "update", "peopleId": 2, "userId": 13, "changes": {"enabled": False}},
                {"kind": "update", "peopleId": 3, "userId": 14, "changes": {"enabled": False}}]
        res = S.apply_actions(FakeClient(), acts, lambda pid, guid: links.__setitem__(pid, guid))
        self.assertEqual(links, {1: "NEWGUID"})
        self.assertEqual([bool(e) for _, e in res], [False, True, False])

    def test_count_writes_ignores_link_bookkeeping(self):
        self.assertEqual(S.count_writes([{"kind": "link"}, {"kind": "create"}, {"kind": "update"}]), 2)


class Person(object):
    def __init__(self, pid):
        self.PeopleId = pid


class FakeQuery(object):
    """Stands in for TouchPoint's q: QueryList takes 1000 people by default, like the real one."""

    def __init__(self, people, cap=None):
        self.people, self.cap, self.limits = people, cap, []

    def QueryCount(self, search):
        return len(self.people)

    def QueryList(self, search, sort="name", limit=1000, offset=0):
        self.limits.append(limit)
        limit = min(limit, self.cap) if self.cap else limit
        return [Person(p) for p in self.people[offset:offset + limit]]


class SearchTests(unittest.TestCase):
    def setUp(self):
        self._q = getattr(S, "q", None)

    def tearDown(self):
        S.q = self._q

    def test_a_search_over_a_thousand_people_is_not_truncated(self):
        S.q = FakeQuery(list(range(1, 2501)))
        self.assertEqual(S.search_people_ids("anything"), set(range(1, 2501)))
        self.assertGreaterEqual(S.q.limits[0], 2500)

    def test_an_empty_search_is_empty(self):
        S.q = FakeQuery([])
        self.assertEqual(S.search_people_ids("anything"), set())


class PeopleDryRunTests(unittest.TestCase):
    def dry(self, **kw):
        config = dict(S.DEFAULT_CONFIG)
        config.update(kw)
        return S.is_dry_run(config)

    def test_defaults_are_dry(self):
        self.assertTrue(self.dry())

    def test_shared_dry_run_off_does_not_make_the_people_sync_live(self):
        self.assertTrue(self.dry(dryRun=False))

    def test_only_both_flags_off_goes_live(self):
        self.assertFalse(self.dry(dryRun=False, peopleDryRun=False))

    def test_shared_dry_run_on_wins(self):
        self.assertTrue(self.dry(dryRun=True, peopleDryRun=False))

    def test_a_string_or_missing_value_stays_dry(self):
        self.assertTrue(self.dry(dryRun=False, peopleDryRun="false"))
        self.assertTrue(self.dry(dryRun=False, peopleDryRun=None))

    def test_a_partial_result_stops_the_sync(self):
        S.q = FakeQuery(list(range(1, 2501)), cap=1000)
        with self.assertRaises(L.AtriumError):
            S.search_people_ids("anything")


class ControlTests(unittest.TestCase):
    def lock(self, **kw):
        base = {"serial": "S", "id": 0, "label": "NDE", "online": True, "battery_low": False,
                "battery_critical": False, "rf_loss": False, "volts": 6.0}
        base.update(kw)
        return base

    def test_worst_locks_sort_first(self):
        res = AC.battery_summary([self.lock(id=0), self.lock(id=1, battery_low=True), self.lock(id=2, battery_critical=True),
                                  self.lock(id=3, online=False)])
        self.assertEqual([s for _, s in res], ["CRITICAL", "OFFLINE", "LOW", "OK"])

    def test_door_names_must_be_configured(self):
        self.assertEqual(AC.resolve_door({"doors": {"Front": {"serial": "S", "id": "2"}}}, "Front"), ("S", 2))
        with self.assertRaises(L.AtriumError):
            AC.resolve_door({"doors": {}}, "Front")

    def test_actions_refused_without_exact_confirmation(self):
        class Boom(object):
            def __getattr__(self, name):
                raise AssertionError("must not reach the controller")
        for confirm in (None, "yes", "Y", True):
            for action in ("unlock", "lockdown_start", "lockdown_stop"):
                with self.assertRaises(L.AtriumError):
                    AC.run_action(Boom(), action, {"doors": {"F": {"serial": "S", "id": 0}}}, "F", 5, confirm)

    def test_unknown_action_refused(self):
        with self.assertRaises(L.AtriumError):
            AC.run_action(object(), "explode", {}, None, 5, "YES")


D = datetime.datetime


class ScheduleTests(unittest.TestCase):
    START = D(2026, 11, 2)

    def test_windows_are_clipped_merged_and_sorted(self):
        w = [(D(2026, 11, 2, 10), D(2026, 11, 2, 12)), (D(2026, 11, 2, 9), D(2026, 11, 2, 10, 30)),
             (D(2026, 11, 1, 23), D(2026, 11, 2, 1)), (D(2026, 11, 8, 23), D(2026, 11, 9, 3))]
        self.assertEqual(L.normalize_windows(self.START, 7, w), [(0, 3600), (32400, 43200), (7 * 86400 - 3600, 7 * 86400)])

    def test_fields_clear_unused_periods(self):
        f = L.schedule_fields(self.START, 7, [(D(2026, 11, 2, 1), D(2026, 11, 2, 2))])
        self.assertEqual((f["dword6_0"], f["dword7_0"], f["dword6_1"], f["dword7_99"]), (3600, 7200, 0, 0))
        self.assertEqual(f["dword5"], 604800)
        self.assertEqual(f["utc_time4"], L.epoch_to_hex(L.datetime_to_epoch(self.START)))

    def test_too_many_periods_refused(self):
        w = [(D(2026, 11, 2) + datetime.timedelta(minutes=30 * i), D(2026, 11, 2) + datetime.timedelta(minutes=30 * i + 10)) for i in range(101)]
        with self.assertRaises(L.AtriumError):
            L.schedule_fields(self.START, 7, w)

    def test_round_trip_through_record(self):
        f = L.schedule_fields(self.START, 7, [(D(2026, 11, 3, 8), D(2026, 11, 3, 9))])
        rec = dict((k, str(v)) for k, v in f.items())
        rec.update({"id": "30", "label3": "x", "ro": "0", "protect": "0"})
        s = L.parse_schedule(rec)
        self.assertEqual(s["periods"], [(32 * 3600, 33 * 3600)])
        self.assertEqual(s["start"], self.START)

    def test_unchanged_schedule_needs_no_write_even_after_start_moves(self):
        yesterday = self.START - datetime.timedelta(days=1)
        f = L.schedule_fields(yesterday, 7, [(D(2026, 11, 3, 8), D(2026, 11, 3, 9))])
        rec = dict((k, str(v)) for k, v in f.items())
        rec.update({"id": "30", "label3": "x", "ro": "0", "protect": "0"})
        self.assertIsNone(SS.plan_schedule(L.parse_schedule(rec), [(D(2026, 11, 3, 8), D(2026, 11, 3, 9))], self.START, 7))

    def test_changed_schedule_is_planned(self):
        rec = dict((k, str(v)) for k, v in L.schedule_fields(self.START, 7, []).items())
        rec.update({"id": "30", "label3": "x", "ro": "0", "protect": "0"})
        plan = SS.plan_schedule(L.parse_schedule(rec), [(D(2026, 11, 3, 8), D(2026, 11, 3, 9))], self.START, 7)
        self.assertEqual((plan["add"], plan["remove"]), (1, 0))

    def sched(self, windows, start=None, cycle=7):
        start = start or self.START
        rec = dict((k, str(v)) for k, v in L.schedule_fields(start, cycle, windows).items())
        rec.update({"id": "30", "label3": "x", "ro": "0", "protect": "0"})
        return L.parse_schedule(rec)

    def test_replace_slice_swaps_only_the_region(self):
        existing = [(D(2026, 11, 2, 8), D(2026, 11, 2, 18))]
        out = SS.replace_slice(existing, [(D(2026, 11, 2, 9), D(2026, 11, 2, 10))], D(2026, 11, 2, 12), D(2026, 11, 2, 16))
        self.assertEqual(sorted(out), [(D(2026, 11, 2, 8), D(2026, 11, 2, 12)), (D(2026, 11, 2, 16), D(2026, 11, 2, 18))])

    def test_near_mode_replaces_slice_and_leaves_everything_else(self):
        s = self.sched([(D(2026, 11, 2, 8), D(2026, 11, 2, 9)), (D(2026, 11, 2, 13), D(2026, 11, 2, 14)),
                        (D(2026, 11, 5, 8), D(2026, 11, 5, 9))])
        now = D(2026, 11, 2, 12)
        plan, reason = SS.plan_schedule_near(s, [(D(2026, 11, 2, 13), D(2026, 11, 2, 15))], now, 4, 7)
        self.assertIsNone(reason)
        got = L.normalize_windows(self.START, 7, plan["raw"])
        want = L.normalize_windows(self.START, 7, [(D(2026, 11, 2, 8), D(2026, 11, 2, 9)), (D(2026, 11, 2, 13), D(2026, 11, 2, 15)),
                                                   (D(2026, 11, 5, 8), D(2026, 11, 5, 9))])
        self.assertEqual(got, want)
        self.assertEqual(plan["start"], self.START)  # near mode never moves the cycle

    def test_near_mode_drops_a_cancelled_reservation_inside_the_slice(self):
        s = self.sched([(D(2026, 11, 2, 13), D(2026, 11, 2, 14))])
        plan, _ = SS.plan_schedule_near(s, [], D(2026, 11, 2, 12), 4, 7)
        self.assertEqual((plan["add"], plan["remove"], plan["windows"]), (0, 1, 0))

    def test_near_mode_with_nothing_to_change_does_nothing(self):
        s = self.sched([(D(2026, 11, 2, 13), D(2026, 11, 2, 14))])
        self.assertEqual(SS.plan_schedule_near(s, [(D(2026, 11, 2, 13), D(2026, 11, 2, 14))], D(2026, 11, 2, 12), 4, 7), (None, None))

    def test_near_mode_defers_to_a_full_run_when_the_cycle_is_stale_or_wrong(self):
        s = self.sched([], start=D(2026, 10, 20))
        plan, reason = SS.plan_schedule_near(s, [], D(2026, 11, 2, 12), 4, 7)
        self.assertIsNone(plan)
        self.assertIn("stale", reason)
        plan, reason = SS.plan_schedule_near(self.sched([], cycle=3), [], D(2026, 11, 2, 12), 4, 7)
        self.assertIsNone(plan)
        self.assertIn("cycle length", reason)

    def test_near_mode_respects_the_end_of_the_cycle(self):
        s = self.sched([])
        now = D(2026, 11, 8, 22)  # 2 h before the cycle ends; a 4 h horizon must be clipped, not spill past it
        plan, _ = SS.plan_schedule_near(s, [(D(2026, 11, 8, 23), D(2026, 11, 9, 3))], now, 4, 7)
        self.assertEqual(L.normalize_windows(self.START, 7, plan["raw"]), [(7 * 86400 - 3600, 7 * 86400)])

    def test_builtin_and_protected_schedules_are_refused(self):
        class C(L.AtriumClient):
            def read(self, *a):
                return {"ro": "0", "protect": "0"} if a[3] > 5 else {"ro": "0", "protect": "0"}
        c = C("http://x", "u", "p", transport=None, master_serial="S")
        with self.assertRaises(L.AtriumError):
            c.set_schedule_windows(1, self.START, 7, [])

        class P(L.AtriumClient):
            def read(self, *a):
                return {"ro": "0", "protect": "1"}
        with self.assertRaises(L.AtriumError):
            P("http://x", "u", "p", transport=None, master_serial="S").set_schedule_windows(30, self.START, 7, [])


class AreaWindowTests(unittest.TestCase):
    DAY = (D(2026, 11, 2), D(2026, 11, 3))

    @staticmethod
    def row(start, end, child=False, status=1, setup=0, teardown=0):
        return {"start": start, "end": end, "event_start": start, "event_end": end, "setup": setup,
                "teardown": teardown, "child": child, "status": status}

    def windows(self, rows, **kw):
        return SS.area_windows(rows, self.DAY[0], self.DAY[1], **kw)

    def test_ordinary_event_opens_the_door_with_padding(self):
        rows = [self.row(D(2026, 11, 2, 10), D(2026, 11, 2, 12))]
        self.assertEqual(self.windows(rows, before=15, after=10), [(D(2026, 11, 2, 9, 45), D(2026, 11, 2, 12, 10))])

    def test_no_events_means_locked_by_default(self):
        self.assertEqual(self.windows([]), [])

    def test_no_events_means_open_when_default_is_unlocked(self):
        self.assertEqual(self.windows([], default_is_locked=False), [self.DAY])

    def test_children_event_locks_20_minutes_either_side(self):
        rows = [self.row(D(2026, 11, 2, 9), D(2026, 11, 2, 17), status=None),
                self.row(D(2026, 11, 2, 12), D(2026, 11, 2, 13), child=True)]
        self.assertEqual(self.windows(rows), [(D(2026, 11, 2, 9), D(2026, 11, 2, 11, 40)),
                                              (D(2026, 11, 2, 13, 20), D(2026, 11, 2, 17))])

    def test_longer_setup_and_teardown_win_over_the_buffer(self):
        rows = [self.row(D(2026, 11, 2, 9), D(2026, 11, 2, 17)),
                self.row(D(2026, 11, 2, 12), D(2026, 11, 2, 13), child=True, setup=45, teardown=10)]
        self.assertEqual(self.windows(rows), [(D(2026, 11, 2, 9), D(2026, 11, 2, 11, 15)),
                                              (D(2026, 11, 2, 13, 20), D(2026, 11, 2, 17))])

    def test_buffer_is_configurable(self):
        rows = [self.row(D(2026, 11, 2, 9), D(2026, 11, 2, 17)),
                self.row(D(2026, 11, 2, 12), D(2026, 11, 2, 13), child=True)]
        self.assertEqual(self.windows(rows, child_buffer=0), [(D(2026, 11, 2, 9), D(2026, 11, 2, 12)),
                                                              (D(2026, 11, 2, 13), D(2026, 11, 2, 17))])

    def test_children_event_alone_gives_no_windows_when_locked_by_default(self):
        self.assertEqual(self.windows([self.row(D(2026, 11, 2, 10), D(2026, 11, 2, 11), child=True)], before=15, after=15), [])

    def test_unlocked_default_is_open_except_around_children_events(self):
        rows = [self.row(D(2026, 11, 2, 10), D(2026, 11, 2, 11), child=True)]
        self.assertEqual(self.windows(rows, default_is_locked=False),
                         [(D(2026, 11, 2), D(2026, 11, 2, 9, 40)), (D(2026, 11, 2, 11, 20), D(2026, 11, 3))])

    def test_unapproved_ordinary_event_does_not_open_the_door(self):
        self.assertEqual(self.windows([self.row(D(2026, 11, 2, 10), D(2026, 11, 2, 11), status=0)]), [])

    def test_pending_children_event_still_locks(self):
        rows = [self.row(D(2026, 11, 2, 9), D(2026, 11, 2, 11)),
                self.row(D(2026, 11, 2, 10), D(2026, 11, 2, 11), child=True, status=0)]
        self.assertEqual(self.windows(rows, child_buffer=0), [(D(2026, 11, 2, 9), D(2026, 11, 2, 10))])

    def test_sql_matches_bvcms_schema(self):
        # Meetings has no Canceled column; DidNotMeet is what marks a meeting that didn't happen.
        for sql in (SS.DIRECT_RESERVATION_SQL, SS.AREA_RESERVATION_SQL):
            self.assertNotIn("Canceled", sql)
            self.assertIn("DidNotMeet", sql)

    def test_reservable_id_mappings_read_services_not_rooms(self):
        # Services are ReservationItems attached to a reservation, not Reservations rows of their own.
        sql = SS.DIRECT_RESERVATION_SQL
        self.assertIn("FROM ReservationItems ri", sql)
        self.assertIn("ri.ReservableId = {rid}", sql)
        self.assertNotIn("r.ReservableId", sql)
        self.assertIn("ri.ApprovalStatus", sql)

    def test_display_name_is_never_blank_and_escapes_markup(self):
        self.assertEqual(SS.display_name("_ Code 01"), "_ Code 01")
        self.assertEqual(SS.display_name("  Door <A> & B  "), "Door &lt;A&gt; &amp; B")
        self.assertEqual(SS.display_name(""), "(no name)")
        self.assertEqual(SS.display_name(None), "(no name)")


def table_client(used, total=2000, cap=None, refuse_over=None):
    """An AtriumClient whose read_range serves a fake record table: ids in `used` are used, the rest free."""
    client = L.AtriumClient("http://x", "u", "p", transport=None, master_serial="S")
    calls = []

    def read_range(serial, obj_type, rec, lo, hi):
        calls.append((lo, hi))
        if refuse_over and hi - lo + 1 > refuse_over:
            raise L.AtriumError("range too wide")
        if cap:
            hi = min(hi, lo + cap - 1)
        return [{"id": str(i), "obj_status": "used" if used(i) else "free"} for i in range(lo, min(hi, total - 1) + 1)]

    client.read_range = read_range
    return client, calls


class RecordWalkTests(unittest.TestCase):
    def test_walks_in_wide_batches_and_stops_after_an_empty_one(self):
        client, calls = table_client(lambda i: i < 340)
        self.assertEqual([int(r["id"]) for r in client.iter_records("user")], list(range(340)))
        self.assertEqual(calls, [(0, 99), (100, 199), (200, 299), (300, 399), (400, 499)])

    def test_a_small_table_that_never_ends_stops_at_its_own_limit_and_shows_a_sample(self):
        # What the live controller did to the access level scan: 50 requests and still going.
        client, calls = table_client(lambda i: True, total=10 ** 6)
        with self.assertRaises(L.AtriumError) as ctx:
            list(client.iter_records("access_lvl"))
        self.assertLessEqual(len(calls), 11)
        self.assertIn("access_lvl", str(ctx.exception))
        self.assertIn("obj_status=used", str(ctx.exception))

    def test_range_reads_that_dont_report_obj_status_fail_fast_with_a_sample(self):
        client = L.AtriumClient("http://x", "u", "p", transport=None, master_serial="S")
        calls = []

        def read_range(serial, obj_type, rec, lo, hi):
            calls.append((lo, hi))
            return [{"id": str(i), "label3": "L{}".format(i)} for i in range(lo, hi + 1)]

        client.read_range = read_range
        with self.assertRaises(L.AtriumError) as ctx:
            list(client.iter_records("access_lvl"))
        self.assertEqual(len(calls), 1)
        self.assertIn("label3=L0", str(ctx.exception))

    def test_rules_with_only_numeric_levels_skip_reading_level_names(self):
        self.assertFalse(S.rules_need_level_names([{"accessLevel": 3}, {"accessLevel": "12"}]))
        self.assertTrue(S.rules_need_level_names([{"accessLevel": 3}, {"accessLevel": "Staff"}]))
        self.assertFalse(S.rules_need_level_names([]))

    def test_falls_back_to_narrow_batches_if_the_controller_refuses_a_wide_range(self):
        client, calls = table_client(lambda i: i < 60, refuse_over=25)
        self.assertEqual(len(list(client.iter_records("user"))), 60)
        self.assertEqual(calls[0], (0, 99))
        self.assertEqual(calls[1], (0, 24))
        self.assertEqual(client.batch_ids, L.FALLBACK_BATCH_IDS)

    def test_a_controller_that_trims_the_range_does_not_make_it_skip_records(self):
        client, _ = table_client(lambda i: i < 340, cap=25)
        self.assertEqual([int(r["id"]) for r in client.iter_records("user")], list(range(340)))

    def test_a_table_that_never_ends_is_an_error(self):
        client, _ = table_client(lambda i: True, total=10 ** 6)
        with self.assertRaises(L.AtriumError):
            list(client.iter_records("user", max_ids=500))

    def test_a_controller_that_ignores_the_range_is_an_error(self):
        client = L.AtriumClient("http://x", "u", "p", transport=None, master_serial="S")
        client.read_range = lambda serial, t, rec, lo, hi: [{"id": str(i), "obj_status": "used"} for i in range(25)]
        with self.assertRaises(L.AtriumError):
            list(client.iter_records("user"))


class TimeBudgetTests(unittest.TestCase):
    class Clock(object):
        def __init__(self):
            self.now = datetime.datetime(2026, 11, 12, 9, 0, 0)

        def __call__(self):
            return self.now

    def client(self, clock):
        c = L.AtriumClient("http://x", "u", "p", transport=None, clock=clock)
        c.transport = lambda method, url, body=None: "ok"
        return c

    def test_requests_are_counted(self):
        c = self.client(self.Clock())
        c._send("GET", "u")
        c._send("POST", "u", "body")
        self.assertEqual(c.request_count, 2)

    def test_a_request_past_the_budget_is_refused(self):
        clock = self.Clock()
        c = self.client(clock)
        c.set_time_budget(60)
        c._send("GET", "u")
        clock.now += datetime.timedelta(seconds=61)
        with self.assertRaises(L.AtriumError):
            c._send("GET", "u")
        self.assertEqual(c.request_count, 1)

    def test_no_budget_means_no_limit(self):
        clock = self.Clock()
        c = self.client(clock)
        c.set_time_budget(60)
        c.set_time_budget(None)
        clock.now += datetime.timedelta(hours=1)
        self.assertEqual(c._send("GET", "u"), "ok")

    def test_phase_timer_reports_seconds_and_requests(self):
        clock = self.Clock()
        c = self.client(clock)
        timer = S.PhaseTimer(c, clock=clock)
        c._send("GET", "u")
        c._send("GET", "u")
        clock.now += datetime.timedelta(seconds=12.5)
        timer.mark("levels")
        c._send("GET", "u")
        clock.now += datetime.timedelta(seconds=30)
        timer.mark("users")
        self.assertEqual(timer.summary(), "levels 12.5s (2 requests); users 30.0s (1 requests).  Total 42.5s.")


if __name__ == "__main__":
    unittest.main()
