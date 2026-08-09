# Pckgd
# Title: SchedulerSyncer
# Description: Apply your scheduler volunteers to the places where they actually serve.
# Updates from: GitHub/TenthPres/TouchPointScripts/SchedulerSyncer/SchedulerSyncer.py
# Version: 1.0.3
# License: AGPL-3.0
# Author: James at Tenth
# Editable: False

# Do not make edits to this file.  They will be overwritten during updates.


global model, q

import json

default_config = {
    "config": [],
    "assignments": {}
}

def get_scheduler_involvements():
    # noinspection SqlResolve
    sql = """
    SELECT o.OrganizationId, 
           o.OrganizationName, 
           oe_ap.BitValue as AssumePresent, 
           oe_ae.BitValue as ApplyElsewhere,
           oe_ge.BitValue as AssignElsewhere
    FROM Organizations o 
    LEFT JOIN OrganizationExtra oe_ap 
            ON o.OrganizationId = oe_ap.OrganizationId AND 'Bit' = oe_ap.Type AND 'Scheduler:AssumePresent' = oe_ap.field
    LEFT JOIN OrganizationExtra oe_ae
              ON o.OrganizationId = oe_ae.OrganizationId AND 'Bit' = oe_ae.Type AND 'Scheduler:ApplyElsewhere' = oe_ae.field
    LEFT JOIN OrganizationExtra oe_ge
              ON o.OrganizationId = oe_ge.OrganizationId AND 'Bit' = oe_ge.Type AND 'Scheduler:AssignElsewhere' = oe_ge.field
    WHERE o.RegistrationTypeId = 22 
        AND o.OrganizationStatusId = 30
    ORDER BY o.OrganizationName;
    """
    return q.QuerySql(sql)


def process_queue():
    sql = """
          -- noinspection SqlResolve
          SELECT
              tsm.MeetingId as MeetingId,
              tsmv.PeopleId as PeopleId,
              tsm.MeetingDateTime as MeetingDate,
              m.OrganizationId,

              oe_ap.BitValue as AssumePresent,
              oe_ae.BitValue as ApplyElsewhere,
              oe_ge.BitValue as AssignElsewhere,

              tsm.TimeSlotId as ScheduleId,
              ts.DayOfWeek,
              ts.TimeOfDay,

              tsmv.TimeSlotTeamId as TeamId,
              tst.TeamName,

              mt.Id as GroupId,
              mt.Name as GroupName,

              a.AttendanceFlag

          FROM TimeSlotMeetingVolunteers tsmv
                   JOIN TimeSlotMeetings tsm ON tsmv.TimeSlotMeetingId = tsm.TimeSlotMeetingId
                   LEFT JOIN TimeSlotTeams tst ON tsmv.TimeSlotTeamId = tst.TimeSlotTeamId
                   JOIN TimeSlots ts ON tsm.TimeSlotId = ts.TimeSlotId AND 0 = ts.IsDeleted
                   JOIN TimeSlotMeetingTeams tsmt ON tsmv.TimeSlotMeetingTeamId = tsmt.TimeSlotMeetingTeamId
                   LEFT JOIN TimeSlotMeetingTeamSubGroups tsmtsg ON tsmv.TimeSlotMeetingTeamSubGroupId = tsmtsg.TimeSlotMeetingTeamSubGroupId
                   LEFT JOIN MemberTags mt ON tsmtsg.MemberTagId = mt.Id
                   JOIN Meetings m ON tsm.MeetingId = m.MeetingId
                   LEFT JOIN OrganizationExtra oe_ap
                             ON m.OrganizationId = oe_ap.OrganizationId AND 'Bit' = oe_ap.Type AND 'Scheduler:AssumePresent' = oe_ap.field
                   LEFT JOIN OrganizationExtra oe_ae
                             ON m.OrganizationId = oe_ae.OrganizationId AND 'Bit' = oe_ae.Type AND 'Scheduler:ApplyElsewhere' = oe_ae.field
                   LEFT JOIN OrganizationExtra oe_ge
                             ON m.OrganizationId = oe_ge.OrganizationId AND 'Bit' = oe_ge.Type AND 'Scheduler:AssignElsewhere' = oe_ge.field
                   LEFT JOIN Attend a
                             ON m.MeetingId = a.MeetingId AND tsmv.PeopleId = a.PeopleId

          WHERE tsmv.IsActive = 1
            AND m.MeetingDate <= DATEADD(HOUR, 4, GETDATE())
            AND m.MeetingDate >= DATEADD(HOUR, -4, GETDATE())
            AND (
              oe_ap.BitValue = 1
                  OR oe_ae.BitValue = 1
                  OR oe_ge.BitValue = 1
              )

          ORDER BY m.OrganizationId, tsm.MeetingDateTime, tsmv.TimeSlotTeamId, mt.Id;
          """

    sched_entries = q.QuerySql(sql)
    current_sched_meeting_id = 0

    config = json.loads(model.TextContent('SchedulerSyncer.json')) or default_config
    sched_config = None

    current_assignments = []

    for s in sched_entries:

        # Handle the "Assume Present", which happens to be super easy.
        if int(s.AssumePresent) == 1 and int(s.AttendanceFlag) != 1:
            model.EditPersonAttendance(s.MeetingId, s.PeopleId, True)

        # if not apply elsewhere or assign elsewhere, no need to continue in loop with slower pieces.
        if int(s.ApplyElsewhere) != 1 and int(s.AssignElsewhere) != 1:
            continue

        # Find the config for this scheduler involvement
        if s.MeetingId != current_sched_meeting_id:
            current_sched_meeting_id = s.MeetingId
            sched_config = None

            for inv in config["config"]:
                if _safe_int(inv.get("orgId")) == s.OrganizationId:
                    sched_config = inv
                    break

        if sched_config is None:
            print("ERROR: Config not found")
            continue

        # Find the target assignment.  schedule, team, group, are the keys in order.
        assignment_key = []

        if sched_config["criteria"]["bySchedule"]:
            assignment_key.append("schedule:" + str(s.ScheduleId))

        if sched_config["criteria"]["byTeam"]:
            assignment_key.append("team:" + str(s.TeamId))

        if sched_config["criteria"]["byGroup"]:
            assignment_key.append("group:" + str(s.GroupId))

        if len(assignment_key) > 0:
            assignment_key = "|".join(assignment_key)
        else:
            assignment_key = "all"

        # find target assignment
        target_assignment = None
        for a in sched_config["assignments"]:
            if a["groupKey"] == assignment_key:
                target_assignment = a
                break

        if target_assignment is None:
            continue

        target_involvement = _safe_int(target_assignment['targetInvolvementId'])

        if target_involvement is None or target_involvement == 0:
            continue

        # Assign Membership if needed
        target_mem_type = _safe_int(target_assignment["memberTypeId"])
        if s.AssignElsewhere and target_mem_type > 0:
            # noinspection SqlResolve
            sql = "SELECT om.memberTypeId FROM OrganizationMembers om WHERE om.PeopleId = {0} AND om.OrganizationId = {1}"
            existing_mem_type = q.QuerySqlInt(sql.format(s.PeopleId, s.OrganizationId)) or 0

            current_assn_key = "{}-{}".format(s.PeopleId, target_involvement)
            if current_assn_key not in current_assignments:
                current_assignments.append(current_assn_key)

            if current_assn_key not in config["assignments"]:
                config["assignments"][current_assn_key] = existing_mem_type

            if not model.InOrg(s.PeopleId, target_involvement):
                model.JoinOrg(target_involvement, s.PeopleId)

            if target_mem_type != existing_mem_type:
                model.SetMemberType(s.PeopleId, target_involvement, _get_memberType_string(target_mem_type))

        # Find the target meeting
        sql = """
        -- noinspection SqlResolve
        SELECT m.MeetingId
        FROM Meetings m 
        WHERE m.MeetingDate = '{0}'
            AND m.OrganizationId = {1}
        """.format(s.MeetingDate, target_assignment['targetInvolvementId'])

        target_meeting = q.QuerySqlInt(sql)

        # TODO revisit if appropriate to create a meeting if one doesn't already exist.
        if target_meeting == 0 or target_meeting is None:
            continue

        if s.ApplyElsewhere:
            if sched_config["attendanceStatus"] == "committed":
                model.EditCommitment(target_meeting, s.PeopleId, "attending")

            elif sched_config["attendanceStatus"] == "present":
                model.EditPersonAttendance(target_meeting, s.PeopleId, True)

    assns_to_pop = []

    for assn in config["assignments"]:
        if assn not in current_assignments:
            [pid, oid] = assn.split("-")
            pid = int(pid)
            oid = int(oid)
            mtid = int(config["assignments"][assn])

            if mtid == 0:
                model.DropOrgMember(pid, oid)
            else:
                model.SetMemberType(pid, oid, _get_memberType_string(mtid))

            assns_to_pop.append(assn)

    for assn in assns_to_pop:
        config["assignments"].pop(assn)

    model.WriteContent("SchedulerSyncer.json", json.dumps(config, indent=2))

def get_member_types():
    return q.QuerySql("""
    -- noinspection SqlResolve
    SELECT Id, Description as Name
    FROM lookup.MemberType
    """)


def get_times_teams_and_groups(org_id):
    sql = """
          SELECT *
          INTO #A
          FROM TimeSlotTeamSubGroups tstsg
                   JOIN MemberTags mt ON tstsg.MemberTagId = mt.Id
          WHERE tstsg.isDeleted = 0
            AND mt.OrgId = {0};


          SELECT tst.TimeSlotTeamId, ts.TimeSlotId, tst.TeamName, ts.DayOfWeek, ts.TimeOfDay, tst.UseSubGroup
          INTO #B
          FROM TimeSlotTeams tst
                   JOIN TimeSlots ts ON tst.TimeSlotId = ts.TimeSlotId AND 0 = ts.IsSingleMeeting AND 0 = ts.IsDeleted
          WHERE tst.IsDeleted = 0
            AND ts.OrganizationId = {0};


          SELECT b.TimeSlotTeamId,
                 b.TimeSlotId,
                 a.TimeSlotTeamSubGroupId,
                 b.TeamName,
                 a.MemberTagId AS SubGroupId,
                 a.Name AS SubGroupName,
                 b.DayOfWeek,
                 b.TimeOfDay,
                 b.UseSubGroup
          FROM #B b
                   LEFT JOIN #A a
                             ON b.TimeSlotTeamId = a.TimeSlotTeamId;
    """.format(org_id)

    return q.QuerySql(sql)


def _get_memberType_string(type_int):
    return q.QuerySqlStr("""
               -- noinspection SqlResolve
               SELECT Description as Name
               FROM lookup.MemberType
                   WHERE ID = {}
               """.format(type_int))


def _to_bool(value):
    if value is None:
        return False
    if value is True:
        return True
    if value is False:
        return False
    try:
        return int(value) == 1
    except:
        text = str(value).strip().lower()
        return text in ("true", "t", "yes", "y", "1")


def _safe_int(value):
    try:
        return int(value)
    except:
        return None


def _build_groups_payload(org_id):
    rows = get_times_teams_and_groups(org_id)
    payload = []

    index = 0
    for row in rows:
        day_of_week = getattr(row, "DayOfWeek", "") or ""
        time_of_day = getattr(row, "TimeOfDay", "") or ""
        team_name = getattr(row, "TeamName", "") or ""
        subgroup_name = getattr(row, "SubGroupName", "") or ""
        schedule_label = "{0} {1}".format(day_of_week, time_of_day).strip()
        selector_label = "{0} {1} {2}".format(schedule_label, team_name, subgroup_name).strip()

        payload.append({
            "orderIndex": index,
            "timeSlotId": getattr(row, "TimeSlotId", None),
            "timeSlotTeamId": getattr(row, "TimeSlotTeamId", None),
            "SubGroupId": getattr(row, "SubGroupId", None),
            "dayOfWeek": day_of_week,
            "timeOfDay": time_of_day,
            "teamName": team_name,
            "groupName": subgroup_name,
            "displayLabel": selector_label
        })
        index += 1

    return payload


def render_settings_interface():
    involvements = get_scheduler_involvements()
    member_types = get_member_types()

    member_type_list = []

    for member_type in member_types:
        member_type_list.append({
            "id": member_type.Id,
            "name": member_type.Name
        })

    json_conf = json.loads(model.TextContent('SchedulerSyncer.json') or "null") or default_config

    default_values = {
        "orgId": 0,
        "orgName": "",
        "assumePresent": False,
        "applyElsewhere": False,
        "assignElsewhere": False,
        "attendanceStatus": "committed",
        "bySchedule": False,
        "byTeam": False,
        "byGroup": False,
        "rowsLoaded": False,
        "assignments": []
    }

    involvement_ids_needing_names = []
    involvement_names_by_id = {}

    # standardize values between SQL and JSON
    for inv in involvements:
        found = None
        for ci in json_conf["config"]:
            if ci.get("orgId") == inv.OrganizationId:
                found = ci
                break

        if found is None:
            found = default_values.copy()
            json_conf["config"].append(found)

        found["orgId"] = inv.OrganizationId
        found["orgName"] = inv.OrganizationName
        found["assumePresent"] = _to_bool(getattr(inv, "AssumePresent", None))
        found["applyElsewhere"] = _to_bool(getattr(inv, "ApplyElsewhere", None))
        found["assignElsewhere"] = _to_bool(getattr(inv, "AssignElsewhere", None))
        criteria = found.get("criteria", {})
        if not isinstance(criteria, dict):
            criteria = {}
        found["bySchedule"] = _to_bool(criteria.get("bySchedule", found.get("bySchedule", False)))
        found["byTeam"] = _to_bool(criteria.get("byTeam", found.get("byTeam", False)))
        found["byGroup"] = _to_bool(criteria.get("byGroup", found.get("byGroup", False)))
        if not isinstance(found.get("assignments"), list):
            found["assignments"] = []

        for a in found["assignments"]:
            if not a.get("targetInvolvementName") and a.get("targetInvolvementId") is not None:
                involvement_ids_needing_names.append(a.get("targetInvolvementId"))

    for iid in involvement_ids_needing_names:
        sql = "SELECT OrganizationName FROM Organizations WHERE OrganizationId = {}".format(int(iid))
        involvement_names_by_id[iid] = q.QuerySqlStr(sql)

    for inv in json_conf["config"]:
        for a in inv["assignments"]:
            a["targetInvolvementName"] = involvement_names_by_id.get(a.get("targetInvolvementId"), "")

    involvements_json = json.dumps(json_conf["config"]).replace("</", "<\\/")
    member_types_json = json.dumps(member_type_list).replace("</", "<\\/")

    # language=HTML
    html = """
           <style>
               .scheduler-involvement {
                   border: 1px solid #ddd;
                   margin: 15px 0;
                   border-radius: 4px;
                   background-color: #fafafa;
               }

               .scheduler-involvement-header {
                   font-weight: bold;
                   font-size: 16px;
               }

               .scheduler-involvement-link {
                   margin-left: 10px;
               }

               .scheduler-feature-checkbox {
                   margin: 10px 0;
               }

               .scheduler-attendance-type {
                   margin: 10px 0 10px 25px;
               }

               .scheduler-assignment-grid {
                   margin: 15px 0 0 25px;
               }

               .scheduler-control-group .checkbox {
                   display: inline-block;
                   margin-right: 20px;
               }

               .scheduler-grid-table {
                   width: 100%;
                   margin-top: 10px;
               }

               .scheduler-grid-row {
                   display: grid;
                   gap: 10px;
                   align-items: center;
                   margin-bottom: 8px;
               }

               .scheduler-grid-row.with-selector.with-member-type {
                   grid-template-columns: 1fr 1fr 1fr;
               }

               .scheduler-grid-row.with-selector.no-member-type {
                   grid-template-columns: 1fr 1fr;
               }

               .scheduler-grid-row.no-selector.with-member-type {
                   grid-template-columns: 1fr 1fr;
               }

               .scheduler-grid-row.no-selector.no-member-type {
                   grid-template-columns: 1fr;
               }

               .scheduler-grid-header {
                   font-weight: bold;
                   border-bottom: 2px solid #ddd;
                   margin-bottom: 10px;
                   padding-bottom: 6px;
               }

               .scheduler-save-btn {
                   margin-top: 20px;
               }

               .scheduler-involvement-search {
                   position: relative;
               }

               .scheduler-search-results {
                   position: absolute;
                   top: 100%;
                   left: 0;
                   right: 0;
                   z-index: 20;
                   margin-top: 2px;
                   max-height: 220px;
                   overflow-y: auto;
                   background-color: #fff;
                   border: 1px solid #ccc;
                   border-radius: 4px;
               }

               .scheduler-search-item {
                   cursor: pointer;
               }
           </style>

           <script src="https://cdnjs.cloudflare.com/ajax/libs/knockout/3.5.3/knockout-latest.js"></script>

           <div id="scheduler-app">
               <div data-bind="foreach: involvements">
                   <div class="scheduler-involvement panel panel-default">
                       <div class="panel-body">
                           <div class="scheduler-involvement-header">
                               <span data-bind="text: orgName"></span>
                               <span class="scheduler-involvement-link">
                            <a data-bind="attr: { href: '/Org/' + orgId() }" target="_blank" title="View Involvement">
                                <i class="glyphicon glyphicon-link"></i>
                            </a>
                        </span>
                           </div>

                           <div class="scheduler-feature-checkbox checkbox">
                               <label><input type="checkbox" data-bind="checked: assumePresent"> Assume Present</label>
                           </div>

                           <div class="scheduler-feature-checkbox checkbox">
                               <label><input type="checkbox" data-bind="checked: applyElsewhere"> Apply Attendance
                                   Elsewhere</label>
                           </div>

                           <div class="scheduler-attendance-type" data-bind="visible: applyElsewhere">
                               <div class="form-group">
                                   <label>Mark attendance elsewhere as:</label>
                                   <select class="form-control" style="width: 220px;"
                                           data-bind="value: attendanceStatus">
                                       <option value="present">Present</option>
                                       <option value="committed">Committed</option>
                                   </select>
                               </div>
                           </div>

                           <div class="scheduler-feature-checkbox checkbox">
                               <label><input type="checkbox" data-bind="checked: assignElsewhere"> Assign
                                   Elsewhere</label>
                           </div>

                           <div class="scheduler-assignment-grid" data-bind="visible: showAssignmentInterface">
                               <div class="scheduler-control-group">
                                   <div class="checkbox"><label><input type="checkbox" data-bind="checked: bySchedule">
                                       By Schedule</label></div>
                                   <div class="checkbox"><label><input type="checkbox" data-bind="checked: byTeam"> By
                                       Team</label></div>
                                   <div class="checkbox"><label><input type="checkbox" data-bind="checked: byGroup"> By
                                       Group</label></div>
                               </div>

                               <div class="scheduler-grid-table">
                                   <div class="scheduler-grid-row scheduler-grid-header" data-bind="css: rowCssMap">
                                       <div data-bind="visible: hasSelectorColumn, text: selectorHeading"></div>
                                       <div>Target Involvement</div>
                                       <div data-bind="visible: assignElsewhere">Member Type</div>
                                   </div>

                                   <div data-bind="foreach: assignments">
                                       <div class="scheduler-grid-row" data-bind="css: $parent.rowCssMap">
                                           <span data-bind="visible: $parent.hasSelectorColumn, text: selectorLabel"></span>
                                           <div class="scheduler-involvement-search">
                                               <input type="text" class="form-control input-sm"
                                                      placeholder="Select Involvement"
                                                      data-bind="textInput: targetInvolvementName, event: { focus: showInvolvementSuggestions, blur: hideInvolvementSuggestions, keyup: onInvolvementSearchKeyup }">
                                               <div class="scheduler-search-results list-group"
                                                    data-bind="visible: showSuggestions">
                                                   <div class="list-group-item scheduler-search-item"
                                                        data-bind="event: { mousedown: clearInvolvementSelection }">
                                                       Select Involvement
                                                   </div>
                                                   <!-- ko foreach: suggestions -->
                                                   <div class="list-group-item scheduler-search-item"
                                                        data-bind="text: name, event: { mousedown: $parent.selectInvolvementSuggestion }"></div>
                                                   <!-- /ko -->
                                                   <div class="list-group-item text-muted"
                                                        data-bind="visible: isSearching">Searching...
                                                   </div>
                                                   <div class="list-group-item text-muted"
                                                        data-bind="visible: showNoSuggestions">No involvements found
                                                   </div>
                                               </div>
                                           </div>
                                           <select class="form-control input-sm"
                                                   data-bind="visible: $parent.assignElsewhere, options: $root.memberTypes, optionsText: 'name', optionsValue: 'id', value: memberTypeId, optionsCaption: 'Select member type'"></select>
                                       </div>
                                   </div>

                                   <div class="text-muted" data-bind="visible: loadingRows">Loading
                                       schedules/groups...
                                   </div>
                                   <div class="text-danger" data-bind="visible: loadError, text: loadError"></div>
                               </div>
                           </div>
                       </div>
                   </div>
               </div>
           </div>

           <script>
               var schedulerInitialInvolvements = @@INVOLVEMENTS_JSON@@;
               var schedulerMemberTypes = @@MEMBER_TYPES_JSON@@;

               function SchedulerAssignmentModel(data, root) {
                   var self = this;
                   data = data || {};
                   self.root = root;
                   self.groupKey = data.groupKey || "all";
                   self.selectorLabel = ko.observable(data.selectorLabel || "");
                   self.targetInvolvementId = ko.observable(data.targetInvolvementId || "");
                   self.targetInvolvementName = ko.observable(data.targetInvolvementName || "");
                   self.memberTypeId = ko.observable(data.memberTypeId || "");
                   self.source = data.source || null;
                   self.suggestions = ko.observableArray([]);
                   self.showSuggestions = ko.observable(false);
                   self.isSearching = ko.observable(false);
                   self.suppressSearch = false;
                   self.hideSuggestionsTimer = null;

                   self.showNoSuggestions = ko.pureComputed(function () {
                       return self.showSuggestions() && !self.isSearching() && self.suggestions().length === 0;
                   });

                   self.applySuggestions = function (items) {
                       self.suggestions(items || []);
                       self.showSuggestions(true);
                   };

                   self.refreshSuggestions = function (term) {
                       self.isSearching(true);
                       self.root.searchInvolvements(term, function (items) {
                           self.isSearching(false);
                           self.applySuggestions(items);
                       });
                   };

                   self.showInvolvementSuggestions = function () {
                       if (self.hideSuggestionsTimer) {
                           clearTimeout(self.hideSuggestionsTimer);
                           self.hideSuggestionsTimer = null;
                       }
                       self.refreshSuggestions(self.targetInvolvementName());
                       return true;
                   };

                   self.hideInvolvementSuggestions = function () {
                       self.hideSuggestionsTimer = setTimeout(function () {
                           self.showSuggestions(false);
                       }, 150);
                       return true;
                   };

                   self.selectInvolvementSuggestion = function (item) {
                       self.suppressSearch = true;
                       self.targetInvolvementId(item.id);
                       self.targetInvolvementName(item.name);
                       self.root.registerInvolvement(item);
                       self.showSuggestions(false);
                       return false;
                   };

                   self.clearInvolvementSelection = function () {
                       self.suppressSearch = true;
                       self.targetInvolvementId("");
                       self.targetInvolvementName("");
                       self.showSuggestions(false);
                       return false;
                   };

                   self.onInvolvementSearchKeyup = function () {
                       var selectedName = self.root.getCachedInvolvementName(self.targetInvolvementId());
                       if (selectedName !== self.targetInvolvementName()) {
                           self.targetInvolvementId("");
                       }
                       self.refreshSuggestions(self.targetInvolvementName());
                       return true;
                   };

                   self.targetInvolvementName.subscribe(function (value) {
                       if (self.suppressSearch) {
                           self.suppressSearch = false;
                           return;
                       }
                       if (!value) {
                           self.targetInvolvementId("");
                       }
                       self.root.queueAutoSave();
                   });

                   self.targetInvolvementId.subscribe(function () {
                       self.root.queueAutoSave();
                   });

                   self.memberTypeId.subscribe(function () {
                       self.root.queueAutoSave();
                   });
               }

               function SchedulerInvolvementModel(data, root) {
                   var self = this;
                   var criteria = data.criteria || {};
                   self.root = root;
                   self.orgId = ko.observable(data.orgId);
                   self.orgName = ko.observable(data.orgName);
                   self.assumePresent = ko.observable(!!data.assumePresent);
                   self.applyElsewhere = ko.observable(!!data.applyElsewhere);
                   self.assignElsewhere = ko.observable(!!data.assignElsewhere);
                   self.attendanceStatus = ko.observable(data.attendanceStatus || "present");
                   self.bySchedule = ko.observable(!!(criteria.hasOwnProperty("bySchedule") ? criteria.bySchedule : data.bySchedule));
                   self.byTeam = ko.observable(!!(criteria.hasOwnProperty("byTeam") ? criteria.byTeam : data.byTeam));
                   self.byGroup = ko.observable(!!(criteria.hasOwnProperty("byGroup") ? criteria.byGroup : data.byGroup));
                   self.rowsLoaded = ko.observable(!!data.rowsLoaded);
                   self.loadingRows = ko.observable(false);
                   self.loadError = ko.observable("");
                   self.rawRows = ko.observableArray([]);
                   self.assignments = ko.observableArray([]);

                   self.showAssignmentInterface = ko.pureComputed(function () {
                       return self.applyElsewhere() || self.assignElsewhere();
                   });

                   self.hasSelectorColumn = ko.pureComputed(function () {
                       return self.bySchedule() || self.byTeam() || self.byGroup();
                   });

                   self.selectorHeading = ko.pureComputed(function () {
                       var parts = [];
                       if (self.bySchedule()) {
                           parts.push("Schedule");
                       }
                       if (self.byTeam()) {
                           parts.push("Team");
                       }
                       if (self.byGroup()) {
                           parts.push("Group");
                       }
                       return parts.join(" / ");
                   });

                   self.rowCssMap = ko.pureComputed(function () {
                       var hasSelector = self.hasSelectorColumn();
                       var hasMemberType = self.assignElsewhere();
                       return {
                           "with-selector": hasSelector,
                           "no-selector": !hasSelector,
                           "with-member-type": hasMemberType,
                           "no-member-type": !hasMemberType
                       };
                   });

                   self.parseDelimitedJson = function (rawResponse) {
                       var startMarker = ">>>>>>>>>>";
                       var endMarker = "<<<<<<<<<<";
                       var payload = rawResponse || "";
                       var startIndex = payload.indexOf(startMarker);
                       var endIndex = payload.lastIndexOf(endMarker);

                       if (startIndex >= 0 && endIndex > startIndex) {
                           payload = payload.substring(startIndex + startMarker.length, endIndex);
                       }

                       return JSON.parse(payload);
                   };

                   self.rebuildAssignments = function () {
                       var grouped = {};
                       var groupedOrder = [];
                       var existingValues = {};
                       var assignmentSnapshots = [];

                       function makeSourceToken(row) {
                           var parts = [];
                           parts.push(String(row.timeSlotId || ""));
                           parts.push(String(row.timeSlotTeamId || ""));
                           parts.push(String(row.SubGroupId || ""));
                           parts.push(String(row.orderIndex || ""));
                           return parts.join("|");
                       }

                       function buildTokenSet(rows) {
                           var set = {};
                           var i;
                           var token;
                           rows = rows || [];
                           for (i = 0; i < rows.length; i++) {
                               token = makeSourceToken(rows[i]);
                               set[token] = true;
                           }
                           return set;
                       }

                       function countOverlap(left, right) {
                           var count = 0;
                           var token;
                           for (token in left) {
                               if (left.hasOwnProperty(token) && right[token]) {
                                   count++;
                               }
                           }
                           return count;
                       }

                       function getBestExistingValue(groupKey, rows) {
                           var newTokenSet;
                           var i;
                           var candidate;
                           var overlap;
                           var best = null;

                           if (existingValues[groupKey]) {
                               return existingValues[groupKey];
                           }

                           newTokenSet = buildTokenSet(rows);
                           for (i = 0; i < assignmentSnapshots.length; i++) {
                               candidate = assignmentSnapshots[i];
                               overlap = countOverlap(candidate.tokenSet, newTokenSet);
                               if (overlap <= 0) {
                                   continue;
                               }
                               if (!best ||
                                       overlap > best.overlap ||
                                       (overlap === best.overlap && candidate.rowCount > best.rowCount) ||
                                       (overlap === best.overlap && candidate.rowCount === best.rowCount && candidate.orderIndex < best.orderIndex)) {
                                   best = {
                                       overlap: overlap,
                                       rowCount: candidate.rowCount,
                                       orderIndex: candidate.orderIndex,
                                       value: {
                                           targetInvolvementId: candidate.targetInvolvementId,
                                           targetInvolvementName: candidate.targetInvolvementName,
                                           memberTypeId: candidate.memberTypeId
                                       }
                                   };
                               }
                           }

                           return best ? best.value : {};
                       }

                       ko.utils.arrayForEach(self.assignments(), function (existingRow) {
                           var sourceRows = existingRow.source || [];
                           existingValues[existingRow.groupKey] = {
                               targetInvolvementId: existingRow.targetInvolvementId(),
                               targetInvolvementName: existingRow.targetInvolvementName(),
                               memberTypeId: existingRow.memberTypeId()
                           };
                           assignmentSnapshots.push({
                               groupKey: existingRow.groupKey,
                               targetInvolvementId: existingRow.targetInvolvementId(),
                               targetInvolvementName: existingRow.targetInvolvementName(),
                               memberTypeId: existingRow.memberTypeId(),
                               tokenSet: buildTokenSet(sourceRows),
                               rowCount: sourceRows.length,
                               orderIndex: sourceRows.length ? (sourceRows[0].orderIndex || 0) : 0
                           });
                       });

                       ko.utils.arrayForEach(self.rawRows(), function (sourceRow) {
                           var keyParts = [];
                           var labelParts = [];
                           var scheduleLabel;
                           var key;

                           if (self.bySchedule()) {
                               scheduleLabel = ((sourceRow.dayOfWeek || "") + " " + (sourceRow.timeOfDay || "")).replace(/\\s+/g, " ").replace(/^\\s+|\\s+$/g, "");
                               keyParts.push("schedule:" + String(sourceRow.timeSlotId || ""));
                               if (scheduleLabel) {
                                   labelParts.push(scheduleLabel);
                               }
                           }
                           if (self.byTeam()) {
                               keyParts.push("team:" + String(sourceRow.timeSlotTeamId || ""));
                               if (sourceRow.teamName) {
                                   labelParts.push(sourceRow.teamName);
                               }
                           }
                           if (self.byGroup()) {
                               keyParts.push("group:" + String(sourceRow.SubGroupId || ""));
                               if (sourceRow.groupName) {
                                   labelParts.push(sourceRow.groupName);
                               }
                           }

                           key = keyParts.length ? keyParts.join("|") : "all";
                           if (!grouped[key]) {
                               grouped[key] = {
                                   key: key,
                                   selectorLabel: labelParts.join(" ").replace(/\\s+/g, " ").replace(/^\\s+|\\s+$/g, ""),
                                   rows: [],
                                   orderIndex: sourceRow.orderIndex
                               };
                               groupedOrder.push(key);
                           }
                           grouped[key].rows.push(sourceRow);
                       });

                       groupedOrder.sort(function (a, b) {
                           var labelA = (grouped[a].selectorLabel || "").toLowerCase();
                           var labelB = (grouped[b].selectorLabel || "").toLowerCase();
                           if (labelA < labelB) {
                               return -1;
                           }
                           if (labelA > labelB) {
                               return 1;
                           }
                           return grouped[a].orderIndex - grouped[b].orderIndex;
                       });

                       self.assignments.removeAll();
                       ko.utils.arrayForEach(groupedOrder, function (groupKey) {
                           var groupedItem = grouped[groupKey];
                           var existing = getBestExistingValue(groupKey, groupedItem.rows);
                           self.assignments.push(new SchedulerAssignmentModel({
                               groupKey: groupKey,
                               selectorLabel: groupedItem.selectorLabel,
                               source: groupedItem.rows,
                               targetInvolvementId: existing.targetInvolvementId || "",
                               targetInvolvementName: existing.targetInvolvementName || "",
                               memberTypeId: existing.memberTypeId || ""
                           }, self.root));
                       });
                   };

                   self.loadRowsFromServer = function () {
                       var xhr;
                       var requestUrl;

                       self.loadingRows(true);
                       self.loadError("");

                       xhr = new XMLHttpRequest();
                       requestUrl = "?a=groups&orgId=" + encodeURIComponent(self.orgId());
                       xhr.open("GET", requestUrl, true);

                       xhr.onreadystatechange = function () {
                           var parsedRows;
                           if (xhr.readyState !== 4) {
                               return;
                           }

                           self.loadingRows(false);
                           if (xhr.status < 200 || xhr.status >= 300) {
                               self.loadError("Unable to load schedules/groups.");
                               return;
                           }

                           try {
                               parsedRows = self.parseDelimitedJson(xhr.responseText);
                           } catch (e) {
                               self.loadError("Invalid schedules/groups response.");
                               return;
                           }

                           self.rawRows(parsedRows);
                           self.rebuildAssignments();
                           self.rowsLoaded(true);
                       };

                       xhr.send();
                   };

                   self.showAssignmentInterface.subscribe(function (isVisible) {
                       if (isVisible) {
                           self.loadRowsFromServer();
                       }
                   });

                   self.assumePresent.subscribe(function () {
                       self.root.queueAutoSave();
                   });
                   self.applyElsewhere.subscribe(function () {
                       self.root.queueAutoSave();
                   });
                   self.assignElsewhere.subscribe(function () {
                       self.root.queueAutoSave();
                   });
                   self.attendanceStatus.subscribe(function () {
                       self.root.queueAutoSave();
                   });

                   self.bySchedule.subscribe(function () {
                       self.rebuildAssignments();
                       self.root.queueAutoSave();
                   });
                   self.byTeam.subscribe(function () {
                       self.rebuildAssignments();
                       self.root.queueAutoSave();
                   });
                   self.byGroup.subscribe(function () {
                       self.rebuildAssignments();
                       self.root.queueAutoSave();
                   });

                   if (data.assignments && data.assignments.length) {
                       for (var j = 0; j < data.assignments.length; j++) {
                           self.assignments.push(new SchedulerAssignmentModel(data.assignments[j], self.root));
                       }
                   }

                   if (self.showAssignmentInterface()) {
                       self.loadRowsFromServer();
                   }
               }

               function SchedulerViewModel() {
                   var self = this;
                   self.memberTypes = schedulerMemberTypes;
                   self.involvements = ko.observableArray([]);
                   self.configJson = ko.observable("");
                   self.involvementCacheById = {};
                   self.selectedInvolvementCache = [];
                   self.involvementSearchCache = {};
                   self.autoSaveDelayMs = 3000;
                   self.autoSaveTimer = null;
                   self.isInitializing = true;
                   self.saveEndpoint = "/PyScriptForm/@@SCRIPT_NAME@@?a=save"

                   self.queueAutoSave = function () {
                       if (self.isInitializing) {
                           return;
                       }
                       if (self.autoSaveTimer) {
                           clearTimeout(self.autoSaveTimer);
                       }
                       self.autoSaveTimer = setTimeout(function () {
                           self.autoSaveTimer = null;
                           self.saveConfiguration();
                       }, self.autoSaveDelayMs);
                   };

                   self.parseDelimitedJsonResponse = function (rawResponse) {
                       const startMarker = ">>>>>>>>>>";
                       const endMarker = "<<<<<<<<<<";
                       let payload = rawResponse || "";
                       const startIndex = payload.indexOf(startMarker);
                       const endIndex = payload.lastIndexOf(endMarker);

                       if (startIndex >= 0 && endIndex > startIndex) {
                           payload = payload.substring(startIndex + startMarker.length, endIndex);
                       }

                       return JSON.parse(payload || "{}");
                   };

                   self.normalizeSearchTerm = function (term) {
                       return (term || "").toLowerCase().replace(/^\\s+|\\s+$/g, "");
                   };

                   self.isArray = function (value) {
                       return Object.prototype.toString.call(value) === "[object Array]";
                   };

                   self.getCachedInvolvementName = function (id) {
                       let key;
                       if (!id && id !== 0) {
                           return "";
                       }
                       key = String(id);
                       if (self.involvementCacheById[key]) {
                           return self.involvementCacheById[key].name;
                       }
                       return "";
                   };

                   self.registerInvolvement = function (item) {
                       let key;
                       let existing;
                       let i;

                       if (!item || (item.id !== 0 && !item.id) || !item.name) {
                           return;
                       }

                       key = String(item.id);
                       existing = {id: item.id, name: item.name};
                       self.involvementCacheById[key] = existing;

                       for (i = 0; i < self.selectedInvolvementCache.length; i++) {
                           if (String(self.selectedInvolvementCache[i].id) === key) {
                               self.selectedInvolvementCache[i] = existing;
                               return;
                           }
                       }

                       self.selectedInvolvementCache.push(existing);
                   };

                   self.extractInvolvementResults = function (payload) {
                       let items;
                       let normalized = [];
                       let i;
                       let row;
                       let id;
                       let name;

                       if (self.isArray(payload)) {
                           items = payload;
                       } else if (payload && self.isArray(payload.Involvements)) {
                           items = payload.Involvements;
                       } else if (payload && self.isArray(payload.Results)) {
                           items = payload.Results;
                       } else if (payload && self.isArray(payload.results)) {
                           items = payload.results;
                       } else if (payload && self.isArray(payload.items)) {
                           items = payload.items;
                       } else if (payload && self.isArray(payload.value)) {
                           items = payload.value;
                       } else {
                           items = [];
                       }

                       for (i = 0; i < items.length; i++) {
                           row = items[i] || {};
                           id = row.id;
                           if (id === undefined || id === null || id === "") {
                               id = row.Id;
                           }
                           if (id === undefined || id === null || id === "") {
                               id = row.organizationId;
                           }
                           if (id === undefined || id === null || id === "") {
                               id = row.OrganizationId;
                           }
                           if (id === undefined || id === null || id === "") {
                               id = row.InvolvementId;
                           }

                           name = row.name || row.Name || row.organizationName || row.OrganizationName || row.Description;
                           if ((id || id === 0) && name) {
                               normalized.push({id: id, name: name});
                           }
                       }

                       return normalized;
                   };

                   self.mergeInvolvementLists = function (primary, secondary) {
                       var seen = {};
                       var merged = [];

                       function appendItems(items) {
                           var i;
                           var item;
                           var key;
                           for (i = 0; i < items.length; i++) {
                               item = items[i];
                               key = String(item.id);
                               if (!seen[key]) {
                                   seen[key] = true;
                                   merged.push(item);
                               }
                           }
                       }

                       appendItems(primary || []);
                       appendItems(secondary || []);
                       merged.sort(function (a, b) {
                           var nameA = (a.name || "").toLowerCase();
                           var nameB = (b.name || "").toLowerCase();
                           if (nameA < nameB) {
                               return -1;
                           }
                           if (nameA > nameB) {
                               return 1;
                           }
                           return 0;
                       });
                       return merged;
                   };

                   self.getSelectedInvolvementMatches = function (term) {
                       const normalizedTerm = self.normalizeSearchTerm(term);
                       let matches = [];
                       let i;
                       let item;
                       let name;

                       for (i = 0; i < self.selectedInvolvementCache.length; i++) {
                           item = self.selectedInvolvementCache[i];
                           name = (item.name || "").toLowerCase();
                           if (!normalizedTerm || name.indexOf(normalizedTerm) >= 0) {
                               matches.push(item);
                           }
                       }

                       return matches;
                   };

                   self.searchInvolvements = function (term, callback) {
                       const normalizedTerm = self.normalizeSearchTerm(term);
                       let cachedMatches = self.getSelectedInvolvementMatches(normalizedTerm);
                       let xhr;
                       let requestUrl;

                       if (!normalizedTerm) {
                           callback(self.mergeInvolvementLists(cachedMatches, []));
                           return;
                       }

                       if (self.involvementSearchCache[normalizedTerm]) {
                           callback(self.mergeInvolvementLists(cachedMatches, self.involvementSearchCache[normalizedTerm]));
                           return;
                       }

                       xhr = new XMLHttpRequest();
                       requestUrl = "/api/v1/Involvements/?terms=" + encodeURIComponent(term) + "&active=true";
                       xhr.open("GET", requestUrl, true);
                       xhr.onreadystatechange = function () {
                           var payload;
                           var results;
                           var i;

                           if (xhr.readyState !== 4) {
                               return;
                           }

                           if (xhr.status < 200 || xhr.status >= 300) {
                               callback(self.mergeInvolvementLists(cachedMatches, []));
                               return;
                           }

                           try {
                               payload = JSON.parse(xhr.responseText || "[]");
                           } catch (e) {
                               callback(self.mergeInvolvementLists(cachedMatches, []));
                               return;
                           }

                           results = self.extractInvolvementResults(payload);
                           for (i = 0; i < results.length; i++) {
                               self.registerInvolvement(results[i]);
                           }
                           self.involvementSearchCache[normalizedTerm] = results;
                           callback(self.mergeInvolvementLists(cachedMatches, results));
                       };
                       xhr.send();
                   };

                   let that = self;

                   self.submitConfiguration = function (configText) {
                       const xhr = new XMLHttpRequest();
                       const body = "configJson=" + encodeURIComponent(configText || "");

                       xhr.open("POST", that.saveEndpoint, true);
                       xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8");
                       xhr.onreadystatechange = function () {
                           var response;
                           if (xhr.readyState !== 4) {
                               return;
                           }

                           if (xhr.status < 200 || xhr.status >= 300) {
                               return;
                           }

                           try {
                               response = self.parseDelimitedJsonResponse(xhr.responseText);
                           } catch (e) {
                               return;
                           }

                           if (response && response.success && typeof response.configJson === "string") {
                               //self.configJson(response.configJson);
                           }
                       };
                       xhr.send(body);
                   };

                   self.saveConfiguration = function (shouldSubmit) {
                       const payload = [];
                       let configText;
                       if (shouldSubmit !== false) {
                           shouldSubmit = true;
                       }

                       ko.utils.arrayForEach(self.involvements(), function (inv) {
                           const item = {
                               orgId: inv.orgId(),
                               assumePresent: inv.assumePresent(),
                               applyElsewhere: inv.applyElsewhere(),
                               attendanceStatus: inv.applyElsewhere() ? inv.attendanceStatus() : null,
                               assignElsewhere: inv.assignElsewhere(),
                               criteria: {
                                   bySchedule: inv.bySchedule(),
                                   byTeam: inv.byTeam(),
                                   byGroup: inv.byGroup()
                               },
                               assignments: []
                           };

                           ko.utils.arrayForEach(inv.assignments(), function (row) {
                               item.assignments.push({
                                   groupKey: row.groupKey,
                                   targetInvolvementId: row.targetInvolvementId(),
                                   memberTypeId: inv.assignElsewhere() ? row.memberTypeId() : null
                               });
                           });

                           payload.push(item);
                       });

                       configText = JSON.stringify(payload, null, 2);
                       self.configJson(configText);
                       if (shouldSubmit) {
                           self.submitConfiguration(configText);
                       }
                   };

                   ko.utils.arrayForEach(schedulerInitialInvolvements, function (invData) {
                       self.involvements.push(new SchedulerInvolvementModel(invData, self));
                   });
                   self.isInitializing = false;
                   self.saveConfiguration(false);
               }

               ko.applyBindings(new SchedulerViewModel(), document.getElementById("scheduler-app"));
           </script>
           """

    html = html.replace("@@INVOLVEMENTS_JSON@@", involvements_json)
    html = html.replace("@@MEMBER_TYPES_JSON@@", member_types_json)
    html = html.replace("@@SCRIPT_NAME@@", model.ScriptName)

    print(html)
    model.Title = "Scheduler Syncer Configuration"


def json_send(data):
    data = json.dumps(data)
    print(">>>>>>>>>>" + data + "<<<<<<<<<<")

def process_save():
    config_json_text = getattr(model.Data, "configJson", "") or ""
    try:
        parsed = json.loads(config_json_text)
    except ValueError:
        json_send({
            "success": False,
            "error": "Invalid JSON"
        })
    else:
        if not isinstance(parsed, list):
            parsed = []

        config = []
        for inv in parsed:
            if not isinstance(inv, dict):
                continue

            org_id = _safe_int(inv.get("orgId"))
            if org_id is None:
                continue

            model.AddExtraValueBoolOrg(org_id, "Scheduler:AssumePresent", bool(inv.get("assumePresent")))
            model.AddExtraValueBoolOrg(org_id, "Scheduler:ApplyElsewhere", bool(inv.get("applyElsewhere")))
            model.AddExtraValueBoolOrg(org_id, "Scheduler:AssignElsewhere", bool(inv.get("assignElsewhere")))

            criteria = inv.get("criteria", {})
            if not isinstance(criteria, dict):
                criteria = {}

            clean_inv = {
                "orgId": org_id,
                "attendanceStatus": inv.get("attendanceStatus") if inv.get("attendanceStatus") in ("present", "committed") else "present",
                "criteria": {
                    "bySchedule": _to_bool(criteria.get("bySchedule", False)),
                    "byTeam": _to_bool(criteria.get("byTeam", False)),
                    "byGroup": _to_bool(criteria.get("byGroup", False))
                },
                "assignments": []
            }

            assignments = inv.get("assignments", [])
            if isinstance(assignments, list):
                for assignment in assignments:
                    if not isinstance(assignment, dict):
                        continue
                    group_key = assignment.get("groupKey", "all")
                    clean_inv["assignments"].append({
                        "groupKey": group_key,
                        "targetInvolvementId": _safe_int(assignment.get("targetInvolvementId")),
                        "memberTypeId": _safe_int(assignment.get("memberTypeId"))
                    })

            config.append(clean_inv)

        config_full = json.loads(model.TextContent('SchedulerSyncer.json')) or default_config
        config_full["config"] = config

        model.WriteContent("SchedulerSyncer.json", json.dumps(config_full, indent=2))
        json_send({
            "success": True,
            "config": config
        })


if model.Data.a == "groups":
    org_id = _safe_int(getattr(model.Data, "orgId", None))
    if org_id is None:
        json_send({"error": "Invalid orgId", "rows": []})
    else:
        json_send(_build_groups_payload(org_id))

elif model.HttpMethod == "post" and model.Data.a == "save":
    process_save()

elif model.Data.a == "process" or model.Data.ScheduledTime != '' or model.FromMorningBatch:
    process_queue()

else:
    render_settings_interface()