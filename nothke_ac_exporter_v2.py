bl_info = {
    "name": "AC Export v2",
    "category": "Import-Export",
    "blender": (2, 80, 0)
}

import subprocess
import bpy
import os
from bpy.props import IntProperty
from bpy.props import StringProperty

err = ""

# OPERATOR
def get_parent_collection_names(collection, parent_names):
    for parent_collection in bpy.data.collections:
        if collection.name in parent_collection.children.keys():
            parent_names.append(parent_collection.name)
            get_parent_collection_names(parent_collection, parent_names)
            return

def turn_collection_hierarchy_into_path(obj):
    parent_collection = obj.users_collection[0]
    parent_names      = []
    parent_names.append(parent_collection.name)
    get_parent_collection_names(parent_collection, parent_names)
    parent_names.reverse()
    return parent_names[0]

def recurLayerCollection(layerColl, collName):
    found = None
    if (layerColl.name == collName):
        return layerColl
    for layer in layerColl.children:
        found = recurLayerCollection(layer, collName)
        if found:
            return found

def get_uv_vtx_count(mesh):
    # Based on https://blender.stackexchange.com/a/44896
    uvs = []
    try:
        for loop in mesh.loops:
            uv_indices = mesh.uv_layers.active.data[loop.index].uv
            uvs.append(tuple(map(lambda x: round(x,3), uv_indices[:])))
        return len(set(uvs))
    except AttributeError:
        return 0

def get_normal_count(mesh):
    # Blender 4.1+ does not require this
    if (4, 1, 0) > bpy.app.version:
        mesh.calc_normals_split()

    #With Help from CarrotKing Marko "Fuxna" Tatalovic
    unique_i_to_ns = []
    seen = set()

    for loop in mesh.loops:
        vertex_index = loop.vertex_index
        index_to_normal = { 'index': vertex_index, 'normals' : tuple(loop.normal)}
        unique_id = (vertex_index, tuple(loop.normal))

        if unique_id not in seen:
            seen.add(unique_id)
            unique_i_to_ns.append(index_to_normal)            
    return len(unique_i_to_ns)

class WM_OT_ACError(bpy.types.Operator):
    bl_label = ""
    bl_idname = "wm.ac_error"
    
    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):
        row = self.layout
        row.label(text=err)

class NOTHKE_OT_ACExport(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.ac_export"
    bl_label = "AC Export"

    kseditor: StringProperty(default='')
    checkcount: bpy.props.BoolProperty(default=True)
  
    def execute(self, context):
        global err

        self.kseditor = context.scene.acexport_kseditor
        self.checkcount = context.scene.acexport_checkcount

        #main(context, self.layer, self.filename)

        #layer = self.layer

        basedir = os.path.dirname(bpy.data.filepath)

        if not basedir:
            self.report({"ERROR"}, "Blend file is not saved")
            return {'FINISHED'}
            
        if not bpy.context.view_layer.objects.active:
            self.report({"ERROR"}, "No active object (select an object)")
            return {'FINISHED'}

        scene = bpy.context.scene
        
        bpy.ops.ed.undo_push(message="Prepare AC FBX")

        # Deselect all
        bpy.ops.object.select_all(action='DESELECT')

        # Find collection
        lc = bpy.context.view_layer.layer_collection
        layerColl = recurLayerCollection(lc, turn_collection_hierarchy_into_path(bpy.context.view_layer.objects.active))
        
        if layerColl is None:
            self.report({"ERROR"}, "Collection " + collectionName + " doesn't exist!")
            return {'FINISHED'}
            
        print('Found collection: ' + layerColl.name)
        bpy.context.view_layer.active_layer_collection = layerColl

        filename = f"{bpy.context.view_layer.active_layer_collection.name}"
        fpath = basedir + '/' + filename

        # select all in collection (and child collections)
        objs = layerColl.collection.all_objects

        for ob in objs:
            ob.select_set(True)

        # check if objects exist
        if not bpy.context.selected_objects:
            self.report({"ERROR"}, "" + collectionName + " collection is empty!")
            return {'FINISHED'}

        # unlink object data
        bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', object=True, obdata=True, material=False, animation=False)
        print('Unlinked objects')

        selection = bpy.context.selected_objects

        #bpy.ops.object.convert(target='MESH') # not working! context is incorrect

        try:
            # make sure all objects..
            for ob in bpy.context.selected_editable_objects:
                # ..are meshes,
                if ob.type == "EMPTY":
                    continue

                if ob.type != "MESH":
                    raise Exception("Object " + ob.name + " is of type " + ob.type + ", but only EMPTY and MESH are valid")

                # ..have at least 1 material slot,
                if not ob.material_slots:
                    raise Exception("Object " + ob.name + " has no materials!")

                # ..have materials assigned to all slots,
                for slot in ob.material_slots:
                    if slot.material is None:
                        raise Exception(ob.name + " has an empty slot without assigned material")


                if self.checkcount:
                    # ..are not vertexless
                    #if len(ob.data.vertices) > 0:
                        #raise Exception("Object " + ob.name + " has no vertices")

                    # ..don't have more than 65535 vertices/normals/uv
                    if len(ob.data.vertices) > 65535:
                        raise Exception("Object " + ob.name + " has more than 65535 vertices")

                    if get_uv_vtx_count(ob.data) > 65535:
                        raise Exception("Object " + ob.name + " has more than 65535 UVs")
                        
                    if get_normal_count(ob.data) > 65535:
                        raise Exception("Object " + ob.name + " has more than 65535 normals")

        except Exception as e:
            bpy.ops.ed.undo_push(message="")
            bpy.ops.ed.undo()
            bpy.ops.ed.undo_push(message="Export AC FBX")

            #self.report({"ERROR"}, str(e))
            err = "AC Export Error: " + str(e)
            bpy.ops.wm.ac_error('INVOKE_DEFAULT')

            # Always finish with 'FINISHED' so Undo is handled properly
            return {'FINISHED'}

        #export
        bpy.ops.export_scene.fbx(
            filepath = fpath + ".fbx", 
            #version = 'BIN7400',
            use_active_collection = True,
            #use_selection = True,
            global_scale = 1,
            apply_unit_scale = False,
            apply_scale_options = 'FBX_SCALE_UNITS',
            object_types = {'EMPTY', 'MESH', 'OTHER'})

        print('Finished AC export to ' + fpath + ' for collection: ' + bpy.context.view_layer.active_layer_collection.name)

        bpy.ops.ed.undo_push(message="")
        bpy.ops.ed.undo()
        bpy.ops.ed.undo_push(message="Export AC FBX")


        if os.path.exists(self.kseditor.replace('"',"")):
            print("Launching ksEditor")
            subprocess.Popen([self.kseditor.replace('"',""), f"{fpath}.fbx"])

        return {'FINISHED'}

# UI PANEL

class NOTHKE_PT_ACExport(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "AC Exporter"
    bl_idname = "NOTHKE_PT_ACExport"
    
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI' #'TOOLS'
    bl_category = 'AC Exporter'

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        row = layout.row()
        row.prop(scene, 'acexport_kseditor')

        row = layout.row()
        row.prop(scene, 'acexport_checkcount')

        # export button, create operator
        row = layout.row()
        op = row.operator('object.ac_export', text='Export FBX')



def register():
    bpy.utils.register_class(NOTHKE_OT_ACExport)

    bpy.types.Scene.acexport_kseditor = bpy.props.StringProperty(
        name="KsEditorAt Path",
        description="Path to KsEditorAt so it can automatically be opened after export, leave blank to disable",
        default = '')
        
    bpy.types.Scene.acexport_checkcount = bpy.props.BoolProperty(
        name="Check vertex count",
        description="Check if vertex, UV and normal count is under 65535 limit on export, may be slow on large projects",
        default = True)
    
    bpy.utils.register_class(NOTHKE_PT_ACExport)
    bpy.utils.register_class(WM_OT_ACError)

def unregister():
    bpy.utils.unregister_class(NOTHKE_OT_ACExport)
    bpy.utils.unregister_class(NOTHKE_PT_ACExport)
    del bpy.types.Scene.acexport_kseditor
    del bpy.types.Scene.acexport_checkcount

if __name__ == "__main__":
    register()
