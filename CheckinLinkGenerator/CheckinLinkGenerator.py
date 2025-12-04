# Pckgd
# Title: Check-in Link Generator
# Description: Kiosks can be configured to sign in automatically with credentials computed by this script.
# Updates from: GitHub/TenthPres/TouchPointScripts/CheckinLinkGenerator/CheckinLinkGenerator.py
# Author: James at Tenth

global model, q

# get profiles
profs = q.QuerySql("SELECT TOP 100 * FROM CheckinProfiles ORDER BY Name")

profileOpts = []
for p in profs:
    profileOpts.append('<option value="{0}">{1}</option>'.format(p.Name.lower(), p.Name))

# language=html
print('''

<div class="form-group">
<label class="control-label" for="cam">Camera</label>
<select class="form-control" data-bind="value: cam" name="cam">
<option value="none">None</option>
<option value="user">User / Front</option>
<option value="environment">Environment / Back</option>
</select>
</div>

<div class="form-group">
<label class="control-label" for="kioskName">Kiosk Name</label>
<input class="form-control" data-bind="value: name" name="kioskName" type="text" />
</div>

<div class="form-group">
<label class="control-label" for="profile">Profile</label>
<select class="form-control" data-bind="value: profile" name="profile">
%s
</select>
</div>

<div class="form-group">
<label class="control-label" for="user">Username</label>
<input class="form-control" data-bind="value: user" name="user" type="text" />
</div>

<div class="form-group">
<label class="control-label" for="pass">Password</label>
<input class="form-control" data-bind="value: pass" name="pass" type="password" />
</div>

<div class="form-group">
<label class="control-label" for="outputUrl">Configured Check-in URL</label>
<input class="form-control" data-bind="value: outputUrl, click: copyContent" name="outputUrl" type="text" />
</div>

      ''' % ('\n'.join(profileOpts)))


# language=html
print('''
<script src="https://cdnjs.cloudflare.com/ajax/libs/knockout/3.5.0/knockout-min.js"></script>
<script>

function LinkGenModel(){
    this.host = "%s";
    this.cam = ko.observable("none");
    this.name = ko.observable("");
    this.profile = ko.observable("");
    this.user = ko.observable("");
    this.pass = ko.observable("");
    
    let model = this;
    
    this.outputUrl = ko.computed(function() {
        let url = model.host + "/CheckIn?";
        if (model.cam() && model.cam() !== "none") { // cam is optional
            url += "cam=" + encodeURIComponent(model.cam()) + "&";
        }
        if (!model.name()) {
            return ""
        } else {
            url += "name=" + encodeURIComponent(model.name()) + "&";
        }
        if (model.profile()) {
            url += "profile=" + encodeURIComponent(model.profile()) + "&";
        }
        if (!model.user() || !model.pass()) {
            return ""
        } else {
            let credentials = model.user() + ":" + model.pass();
            let encodedCreds = btoa(credentials);
            url += "id=" + encodeURIComponent(encodedCreds);
        }
        return url;
    });
    
    this.copyContent = function() {
        let copyText = model.outputUrl();
        if (!copyText) {
            return;
        }
        navigator.clipboard.writeText(copyText).then(function() {
            swal("Copied the URL to clipboard.");
        }, function(err) {
            console.warn("Could not copy text: ", err);
        });
    };
}
    
ko.applyBindings(new LinkGenModel());
    
</script>''' % (model.CmsHost))
