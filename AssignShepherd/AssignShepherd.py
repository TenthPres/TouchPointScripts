# noinspection PyUnresolvedReferences
import clr

clr.AddReference('System.Web.Extensions')

# noinspection PyUnresolvedReferences
from System.Web.Script.Serialization import JavaScriptSerializer



ShepheredExtraValueName = "Shepherd PID"

# just leave these alone.
userPerson = model.GetPerson(model.UserPeopleId)
editable = False

# Define who should be able to change assignments.
if userPerson.Users[0].InRole('Admin') or userPerson.Users[0].InRole('Officer') or model.InOrg(userPerson.PeopleId, 61):  # org 61 is staff, for our asst ministers
    editable = True

# Cool.  That's all the configuration you need to do. 
###########################################################################


query = q.BlueToolbarReport()
count = q.BlueToolbarCount()

if Data.ShepId != '':
    search = "FamilyExtraInt( Name='{}' ) = {}".format(ShepheredExtraValueName, userPerson.PeopleId)
    query = q.QueryList(search)
    count = q.QueryCount(search)


if model.HttpMethod == "get" and Data.submit == '' and count > 0:
    # Group people by family
    families = {}
    for p in query:
        fid_s = str(p.FamilyId)
        
        if not fid_s in families:
            families[fid_s] = {
                'name': 'The ' + p.Family.HeadOfHousehold.Name + " Family",
                'members': [p]
            }
        else:
            families[fid_s]['members'].append(p)
            
    # prep list of potential shepherds
    if editable:
        elds = q.QueryList('IsMemberOf( Org=124[Session] ) = 1[True]')
        diac = q.QueryList('IsMemberOf( Org=125[Diaconate] ) = 1[True]')
    
    # generate the table
    print "<style>th { border-top: solid 1px #ccc; }</style>"
    print "<table style=\"width:100%; max-width:1000px;\"><tbody>"    
    for f in families:
        print "<tr>"
        
        print "<th>{}</th>".format(families[f]['name'])
        
        p = families[f]['members'][0]
        
        shepherd = model.ExtraValueIntFamily(p.PeopleId, ShepheredExtraValueName)
        shepherd = None if shepherd == 0 else model.GetPerson(shepherd)
        if shepherd is None:
            print "<th id=\"assignment-{0}\"></th>".format(p.PeopleId)
        else:
            print "<th id=\"assignment-{0}\"><a href=\"/Person2/{1}/\">{2}</a></th>".format(p.PeopleId, shepherd.PeopleId, shepherd.Name)
        
        
        if editable:
            print "<td>"
            
            print "<select name=\"assign-{}\" onchange=\"submitChanges(this);\">".format(p.PeopleId)
            print "<option value=\"0\">Select a new Shepherd</option>"
            
            print "<optgroup label=\"Elders\">"
            for s in elds:
                print "<option value=\"{}\">{}</option>".format(s.PeopleId, s.Name)
            print "</optgroup>"
            
            print "<optgroup label=\"Diaconate\">"
            for s in diac:
                print "<option value=\"{}\">{}</option>".format(s.PeopleId, s.Name)
            print "</optgroup>"
            
            print "</select>"
            
            print "</td>"
        
        
        
        print "</tr>"
        print "<tr><td colspan=\"{}\"><ul>".format(3 if editable else 2)
        for p in families[f]['members']:
            print "<li><a href=\"/Person2/{}/\">{}</a></li>".format(p.PeopleId, p.Name)
        print "</ul></td></tr>"
    
    print "</tbody></table>"
    
    if editable:
        print """
        
        <script>
        
        function submitChanges(selectElt) {
            
            let params = {
                submit: 1,
                shepherd: parseInt(selectElt.value),
                sheep: parseInt(selectElt.name.split('-', 2)[1])
            }
            
            //console.log(params)
            
            let xhr = new XMLHttpRequest();
            xhr.addEventListener("load", reqListener);
            xhr.open("POST", \"""" + "/PyScriptForm/" + model.ScriptName + "/" + """?" + new URLSearchParams(params));
            xhr.send();
            
            function reqListener() {
                let start = this.responseText.indexOf(">>DATA>") + 7,
                    data = JSON.parse(this.responseText.substr(start, this.responseText.indexOf("<DATA<<") - start))
                
                if (data.success) {
                    document.getElementById('assignment-' + params.sheep).innerHTML = data.shepherdName
            
                    selectElt.selectedIndex = 0;
                }
            }
        }
        
        </script>
        
        """
elif model.HttpMethod == "post" and Data.submit == '1':
    try:
        shepherd = model.GetPerson(Data.shepherd)
        sheep = model.GetPerson(Data.sheep)
        
        model.AddExtraValueIntFamily(sheep.PeopleId, ShepheredExtraValueName, shepherd.PeopleId)
        
        out = {
            'success': True,
            'shepherdName': shepherd.Name 
        }
        
    except:
        out = {
            'success': False
        }
    
    print "<!-- >>>>>DATA>" + JavaScriptSerializer().Serialize(out) + "<DATA<<<<< -->"
    
else:
    print """It seems you came across this in a way that won't work.  To view or make shepherding assignments, go to a profile or search.  Then, go to 
    the blue toolbar's &lt;/&gt; menu and Select the Assign Shepherd report."""
