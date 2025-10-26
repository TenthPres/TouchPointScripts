# Pckgd

Pckgd (pronounced "packaged") is a lightweight package manager for projects build upon TouchPoint's Python and SQL 
capabilities with less complexity than manually managing files in the Special Content area. 

## Installation
1.  Download the Pckgd zip file from [the releases](https://github.com/TenthPres/TouchPointScripts/releases) and upload the whole zip file to 
    `mychurch.tpsdb.com/InstallPyScriptProject`.  This will install the script.
2.  Navigate to `mychurch.tpsdb.com/PyScript/Pckgd` to get started.  Scripts that you have manually installed before
    installing Pckgd are likely missing the special required headers that Pckgd needs to identify them as packages, 
    which means you may need to manually update them in Special Content one more time.

## Documentation for Package Developers

Packages are identified with a simple set of comments included in the script file, called 'headers.'  The headers must 
be located in the first 100 lines of the script, and must be located immediately together. If a "stop editing" 
demarcation is used (explained below), the headers must be *above* the demarcation. 
The headers are:

- `# Pckgd` - Required.  No value.  Identifies the file as part of a Pckgd package. Without this header, the script won't be found in 
    the query for packages.
- `# Updates from:` - Required for updates. An identifier of where updates should come from.  Two types of values are allowed:
    - A URL to a text file: e.g. `# Updates from: https://example.com/mypackage-latest.txt`
    - A GitHub repository in the format `GitHub/username/repo/path/to/file.py`: e.g. `# Updates from: GitHub/TenthPres/TouchPointScripts/Pckgd/Pckgd.py`
- `# Title:` - Optional, but recommended. The human-readable name of the package.  This is the name shown in the UI. 
- `# Description:` - Optional, but recommended. A brief description of what the package does.
- `# Depends on:` - Optional.  A comma-separated list of other Pckgd scripts (with extensions) that this script depends 
on. For example, if a python script depends on a SQL file, this header might be something like `# Depends on: MyScript.sql`.  
When dependencies are defined, they will be provided as part of installation, provided they are available in the same 
source and directory as the current file. 
- `# Version` - Optional.  The current version of the script.  If not provided, a hash will be generated on a per-file basis to determine if a new version is available.
- `# License:` - Optional.  The license under which the package is provided.
- `# Author:` - Optional.  The author of the package.
- `# Header color:` - Optional.  A hex color code (e.g. `#FF0000`) to use as the header color in the UI.  If one is not provided, a color is generated from a hash of the file name. 
- `# Header image:` - Optional.  A URL to an image to use as the header image in the UI.

### Examples

A well-documented python file with a few dependencies may have a headers like this:
```python
# Pckgd
# Updates from: GitHub/TenthPres/TouchPointScripts/SamplePackage/MyPackage.py
# Title: My Package
# Description: This package does something useful.
# Depends on: SomeDependency.sql, AnotherDependency.py
# Version: 1.0.0
# License: MIT
```

A minimally-documented SQL file may have headers like this:
```sql
-- Pckgd
-- Updates from: https://example.com/mypackage-latest.sql
```

### "Stop editing" demarcation

Some scripts may require that some variables or constants be set for the script to work properly, particularly to 
adapt the script to the specific needs of a given church.  These variables must be near the top of the script, and 
should be separated from the rest of the script with a "stop editing" demarcation, like this:

```python
# ========== DO NOT EDIT BELOW THIS POINT ==========
```

This is crucial for two reasons: 
1. When packages are installed, only content below this line will be replaced.  This allows for customizations to be 
   preserved.
2. When files are evaluated to see if updates are needed, only the content below this line is considered. This allows 
   for customizations to exist and also not interfere with update detection.

If a script does not have any customizations or provides though customizations through a UI, you do not need to include 
a demarcation. 