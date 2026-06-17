import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
arm = bpy.data.armatures.new("TestArm")
obj = bpy.data.objects.new("TestArmObj", arm)
bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.mode_set(mode='EDIT')
b = arm.edit_bones.new("TestBone")
b.head = (0,0,0)
b.tail = (0,1,0)
bpy.ops.object.mode_set(mode='OBJECT')
bone = arm.bones[0]
print("bone select attrs:", [a for a in dir(bone) if 'select' in a.lower()])
# Try pose bone
bpy.ops.object.mode_set(mode='POSE')
pb = obj.pose.bones[0]
print("pose bone select attrs:", [a for a in dir(pb) if 'select' in a.lower()])
bpy.ops.object.mode_set(mode='OBJECT')
