

# Pckgd
# Title: Calendar Signage
# Description: Print signage for rooms and events from configured templates
# Updates from: GitHub/TenthPres/TouchPointScripts/Calendar/CalendarSignage.py
# Author: James at Tenth

global q, model, Data

def get_reservations_for_room(reservableIds, startDate, days):

    if not isinstance(reservableIds, list):
        reservableIds = [reservableIds]

    query = '''
        SELECT  
        rb.ReservableId,
        rv.MeetingStart,
        COALESCE(rv.MeetingEnd, rv.MeetingStart) as MeetingEnd, 
        COALESCE(NULLIF(rv.SetupMinutes, ''), 0) as SetupMinutes,
        COALESCE(NULLIF(rv.SetupMinutes, ''), 0) as TeardownMinutes,
        COALESCE(NULLIF(m.Description, ''), o.OrganizationName) as Name,
        0 as Quantity,
        m.MeetingId,
        o.LeaderName
    INTO #reservables
    FROM Reservations rv
        JOIN Reservable rb ON rv.ReservableId = rb.ReservableId
        JOIN Meetings m ON rv.MeetingId = m.MeetingId
        JOIN Organizations o ON m.OrganizationId = o.OrganizationId
    WHERE rv.MeetingId IS NOT NULL 
        AND rv.MeetingEnd > '{0}'
        AND rv.MeetingStart < DATEADD(day, 1, '{0}');
    '''.format(reservableIds)


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
    WHERE 1=1
        AND ReservableTypeId = {}
        AND IsDeleted = 0
        AND IsEnabled = 1
        
    ORDER BY ReservableTypeId, Name
    ;
""".format(typ))

_config = None

def get_config(asJson = False):
    global _config
    
    if _config is None:
    
        # noinspection PyBroadException
        try:
            _config = model.Content("CalendarSignageConfiguration.json")
        except:
            print("<p>Caution: could not load existing configuration, starting fresh.</p>")
            _config = None
    
        if _config is None or _config.strip() == "":
            _config = "[]"
    
    if asJson:
        return _config
        
    import json
        
    return json.loads(_config)


if model.HttpMethod == "post" and Data.v == "saveSigns":
    # save signage configuration
    import json

    rawData = Data.data
    try:
        signageData = json.loads(rawData)
        model.WriteContentText("CalendarSignageConfiguration.json", json.dumps(signageData), "CalendarSignage")
        print(json.dumps({"status": "success"}))
    except Exception as e:
        model.Log("Error parsing signage data: {}".format(str(e)))
        print(json.dumps({"error": "data parsing error"}))



elif Data.v == "":
    # configuration mode

    # language=html
    model.Title = "Calendar Signage Configuration"

    originalConfig = get_config()

    ko_form = """
    <script>
        const originalData = {};
    </script>
    """.format(originalConfig)

    # Form that lists signs in the system
    # language=html
    ko_form = ko_form + """
              <script src="https://cdnjs.cloudflare.com/ajax/libs/knockout/3.5.0/knockout-min.js"></script>


              <table style="border-collapse: collapse; width: 100%;" data-bind="visible: signs().length > 0">
                  <thead>
                  <tr>
                      <th>Name</th>
                      <th>Sign Template</th>
                      <th>Print Copies</th>
                      <th>Items</th>
                      <th>Options</th>
                  </tr>
                  </thead>
                  <tbody data-bind="foreach: signs">
                  <tr>
                      <td><input data-bind="value: name"/></td>
                      <td><select
                              data-bind="options: $parent.types, optionsText: 'name', optionsValue: 'fileName', value: type">
                      </td>
                      <td><input type="number" data-bind="value: copies" min="0" max="999" /></td>
                      <td><a data-bind="text: items().length, click: $parent.editSign"></a></td>
                      <td>
                          <a data-bind="attr: { href: previewLink }" title="Preview" class="fa fa-eye"></a>
                          <a data-bind="click: $parent.removeSign" title="Remove" class="fa fa-trash"></a>
                      </td>
                  </tr>
                  </tbody>
              </table>
              <a data-bind="click: addSign" class="fa fa-plus" title="Add Sign"></a>


              <div class="modal" id="edit-sign-dialog" data-keyboard="false" data-backdrop="static" style="background: #0009;">
                  <div class="modal-dialog modal-md" data-bind="if: currentlyEditingSign() !== null">
                      <div class="modal-content">
                          <div class="modal-header">
                              <button type="button" class="close" data-dismiss="modal" data-bind="click: closeModal" aria-label="Close"><span aria-hidden="true">×</span></button>
                              <h4 class="modal-title" data-bind="text: 'Editing ' + currentlyEditingSign().name()"></h4>
                          </div>
                          <div class="modal-body">
                              <div class="form-group">
                                  <label for="OrganizationName" class="control-label">Name</label>
                                  <input class="form-control" type="text" data-bind="value: currentlyEditingSign().name" />
                              </div>
                              <div class="form-group">
                                  <label for="InvolvementType" class="control-label">Involvement Type</label>
                                  <select class="form-control" data-val="true" data-val-number="The field Organization Type must be a number." id="org_OrganizationTypeId" name="org.OrganizationTypeId"><option value="0">(not specified)</option>
                                      <option value="2">Children/Youth Program</option>
                                      <option value="10">Small Group</option>
                                      <option value="20">Adult Class</option>
                                      <option value="40">Missions Trip</option>
                                      <option value="49">Job Application</option>
                                      <option selected="selected" value="50">Administration</option>
                                      <option value="51">Parish Council</option>
                                      <option value="70">Social Event</option>
                                      <option value="75">Conference</option>
                                      <option value="81">Worship Services</option>
                                      <option value="91">Communications</option>
                                      <option value="92">Mobile App</option>
                                  </select>
                              </div>
                          </div>
                      </div>
                  </div>
              </div>
              
              
              
              
              <script>
                  function Sign(data) {
                      const that = this;
                      this.name = ko.observable(data.name);
                      this.items = ko.observableArray(data.items || []);
                      this.copies = ko.observable(data.copies || 1);
                      this.type = ko.observable(data.type || "CalendarSignageDirectional");
                      this.id = ko.observable(data.id || btoa(Math.random().toString()).substring(0, 6));
                      this.previewLink = ko.computed(function () {
                          return "?v=" + that.id();
                      });
                      
                      
                      this.copies.subscribe((newValue) => {if (newValue < 0) {this.copies(0)}})
                      this.copies.subscribe(() => window.signageViewModel.saveSigns());
                      this.name.subscribe(() => window.signageViewModel.saveSigns());
                      this.type.subscribe(() => window.signageViewModel.saveSigns());
                      this.items.subscribe(() => window.signageViewModel.saveSigns());
                      
                      this.toJson = function () {
                            return {
                                name: that.name(),
                                items: that.items(),
                                copies: that.copies(),
                                type: that.type(),
                                id: that.id()
                            };
                      };
                  }

                  function ViewModel(data) {
                      const self = this;
                      self.signs = ko.observableArray([]);
                      
                      data.forEach(function (signData) {
                          self.signs.push(new Sign(signData));
                      });

                      self.types = ko.observableArray([
                          {name: "Directional", fileName: "CalendarSignageDirectional"},
                          {name: "Reservations", fileName: "CalendarSignageReservations"},
                          {name: "Event Details", fileName: "CalendarSignageEventDetails"}
                      ]);
                      
                      self.currentlyEditingSign = ko.observable(null);

                      self.currentlyEditingSign.subscribe(() => {
                          console.log("here");
                          console.log(self.currentlyEditingSign())
                          if (self.currentlyEditingSign() !== null) {
                              $('#edit-sign-dialog').fadeIn();
                          } else {
                              $('#edit-sign-dialog').fadeOut();
                          }
                      });
                      
                      self.closeModal = function () {
                          self.currentlyEditingSign(null);
                      }

                      self.addSign = function () {
                          const newSign = new Sign({name: "New Sign"});
                          self.signs.push(newSign);
                          return newSign;
                      };
                      
                      self.editSign = function (sign) {
                          self.currentlyEditingSign(sign);
                      };

                      self.removeSign = function (sign) {
                          self.signs.remove(sign);
                      };
                      
                      self.toJson = function () {
                            return ko.toJS(self.signs().map(s => s.toJson()));
                      };

                      self.saveSigns = function () {
                          // Save signs to server
                          const formData = new URLSearchParams();
                          formData.append('data', JSON.stringify(self.toJson()));

                          // post to ?v=saveSigns
                          fetch("/PyScriptForm/CalendarSignage?v=saveSigns", {
                              method: "POST",
                              credentials: 'include',
                              body: formData
                          }).then(response => {
                              if (!response.ok) {
                                  throw new Error("Network response was not ok"); 
                              }
                              return response.json();
                          }).then(() => {
                              console.log("Signs saved successfully!");
                          })
                      };

                      self.signs.subscribe(function (newSigns) {
                          // Save signs to server on change
                          self.saveSigns()
                      });
                  }

                  window.signageViewModel = new ViewModel(originalData);
                  ko.applyBindings(window.signageViewModel);
              </script>
              """

    print(ko_form)
    
    # print("<p>Select Items to print signage for</p>")
    # print("<table>")
    # for i in [(1, "Rooms"), (2, "Jawns"), (3, "Other Jawns")]:
    #     print("<tr><td colspan=\"2\"><h2>{}</h2></td></tr>".format(i[1]))
    #     l = get_reservables(i[0])
    #     if l:
    #         for r in l:
    #             print("""
    #             <tr>
    #                 <td><input type="checkbox" id="{1}" /></td>
    #                 <td><label for="{1}">{0}</label></td>
    #             """.format(r.Name, r.ReservableId))
    #
    #             if i[0] == 1:
    #                 print("""
    #                 <td><input type="checkbox" id="children-{1}" /></td>
    #             """.format(r.Name, r.ReservableId))
    #
    #             else:
    #                 print("<td></td>")
    #
    #             print("</tr>")
    # print("</table>")
    

# a view, presumably
else:
    reports = (Data.v or "").split(",")
    
    for r in reports:
        pass



#
