"""
Runs AtriumLib's real record-table scan against a controller from a workstation (Python 3, not TouchPoint) and prints
what each request did.  Read-only, and it prints counts only, never record contents, so it is safe to run on the user
table too.

Credentials come from the environment (ATRIUM_URL, ATRIUM_USER, ATRIUM_PASS).

Usage (from AtriumControl/):
    python tools/atrium_walk.py access_lvl
    python tools/atrium_walk.py user 2000        # stop after reading 2000 ids
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import AtriumLib as L  # noqa: E402


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    table = argv[0]
    max_ids = int(argv[1]) if len(argv) > 1 else None

    # ATRIUM_SERIAL, if set, is used as the controller serial in place of the one the login reports.
    client = L.AtriumClient(os.environ["ATRIUM_URL"], os.environ["ATRIUM_USER"], os.environ["ATRIUM_PASS"],
                            L.urllib_transport(30), master_serial=os.environ.get("ATRIUM_SERIAL") or None)
    real_read_range = client.read_range

    def logged(serial, obj_type, rec, lo, hi):
        began = time.time()
        rows = real_read_range(serial, obj_type, rec, lo, hi)
        used = sum(1 for r in rows if r.get("obj_status") == "used")
        print("read ids {}-{} from controller {}: {} rows, {} used, {:.1f}s".format(
            lo, hi, serial, len(rows), used, time.time() - began))
        if rows and not used:
            print("  first record came back as: {}".format(dict(rows[0])))  # an error row carries no record data
        return rows

    client.read_range = logged
    began = time.time()
    count = sum(1 for _ in client.iter_records(table, max_ids=max_ids))
    print("{} records in {}, {} requests, {:.1f}s".format(count, table, client.request_count, time.time() - began))
    if client.fallback_reason:
        print("A wide read failed and the scan dropped to {} ids per request: {}".format(
            client.batch_ids, client.fallback_reason))


if __name__ == "__main__":
    main(sys.argv[1:])
