## blender_ac_exporter
This script exports fbx for Assetto Corsa tracks in a single click. Created for fast iteration in mind, primarily to make sure all objects are properly setup, avoid opening export dialogue every time and since ksEditor is extremely slow and a terrible experience overall, where getting a single thing wrong can easily lose you 5+ minutes for no reason.

## What does it exactly do?
- Makes sure all objects are unlinked (because cloned objects (copied with alt + D) will have spurrious materials when exported to fbx)
- Makes sure at least one material slot is present on all objects and all slots have materials assigned (because objects with no or invalid slots will get autocreated FBX_MATERIALs)
- Makes sure meshes don't have more than 65k vertices/normals/uvs (because AC works with 16bit indices)
- Sets correct fbx export units and settings
- Opens [KsEditorAt](https://ascobash.wordpress.com/2015/07/22/kseditor/) with the exported FBX file. Make sure the path to KsEditorAt is set correctly (you can use shift right click -> copy as path).

### How to install
1. Edit > Preferences.. > Add-Ons > Install.. and select nothke_ac_exporter_v2.py, then activate it on the checkbox
2. A new tab will appear on the right of the viewport called "ACExporter"

### How to use
1. Select an object from the collection you want to export or the collection itself.
2. Open the ACExport tab: On the right side of the viewport > ACExporter
3. Hit "Export FBX". If there are were no warnings, now be in the same folder where .blend is. KsEditorAt will also open if you have given the path to it.

You can also bind a shortcut to the "Export FBX" button by right clicking it and clicking "Assign Shortcut"