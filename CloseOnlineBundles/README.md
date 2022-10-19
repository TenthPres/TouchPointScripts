# Close Online Bundles

This simple script will automatically close online bundles that are at least 4 days old. It does not "post" the bundles, so your Post Date
will be blank.

## Setup

1. In Special Content, create a new Python file called `CloseOnlineBundles` and put in the content of CloseOnlineBundles.py. 
2. Create or edit a python file called "MorningBatch".  Add this command on its own line: `model.CallScript("CloseOnlineBundles")`