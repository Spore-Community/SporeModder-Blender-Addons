__Author__ = 'Allison'

import bpy
import math


# Geometry Nodes

def object_set_geo_node(obj, node_group):
	geo_mod = obj.modifiers.new(name="InstanceBuildings", type='NODES')
	geo_mod.node_group = node_group
	geo_mod.show_in_editmode = False

# TODO: fix scaling to be handled local to the empty object, not along the mesh.
def create_geonode_buildings():
	return create_vertex_geonode(name = "Buildings", displaysize=2.5, scale=(1,1,1.5), offset=(0,0,3.75))

def create_geonode_turrets():
	return create_vertex_geonode(name = "Turrets", displaytype="SPHERE", displaysize=2.1,)

def create_geonode_decor():
	return create_vertex_geonode(name = "Decor", displaytype="SPHERE", scale=(1,1,0))

def create_geonode_gates():
	return create_vertex_geonode(name = "Gates", scale=(1,1,0.5), offset=(0,0,-0.5))

# Create a geometry node that places "empties" on mesh vertices
def create_vertex_geonode(name : str, displaytype='CUBE', displaysize=2, scale=(1,1,1), offset=(0,0,0), rotation=(0,0,0)):
	# Create and return a Geo Node to place Empties on building/tool locations
	# Create a new geometry node modifier
	node_group = bpy.data.node_groups.new('Instance' + name.capitalize() + "Group", 'GeometryNodeTree')

	# Add Geo nodes
	nodes = node_group.nodes
	links = node_group.links

	### Input / Output
	# Group Input
	group_input = nodes.new(type="NodeGroupInput")
	group_input.location = (-400, 0)

	# Group Output
	group_output = nodes.new(type="NodeGroupOutput")
	group_output.location = (400, 0)
	node_group.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
	node_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

	# Create a primitive mesh geonode
	geomesh = None
	if displaytype == 'CUBE':
		geomesh = nodes.new(type="GeometryNodeMeshCube")
		geomesh.inputs['Size'].default_value = (displaysize * 2, displaysize * 2, displaysize * 2)
	elif displaytype == 'CIRCLE':
		geomesh = nodes.new(type="GeometryNodeMeshCircle")
		geomesh.inputs['Radius'].default_value = displaysize
	elif displaytype == 'SPHERE':
		if scale[2] == 0:
			geomesh = nodes.new(type="GeometryNodeMeshCircle")
			geomesh.inputs['Radius'].default_value = displaysize
		else:
			geomesh = nodes.new(type="GeometryNodeMeshUVSphere")
			geomesh.inputs['Radius'].default_value = displaysize
	if geomesh:
		geomesh.location = (-600, -100)

	# Instance on Points
	point_instance = nodes.new(type="GeometryNodeInstanceOnPoints")
	point_instance.location = (0, -100)

	# Transform
	transform = nodes.new(type="GeometryNodeTransform")
	transform.location = (-400, -100)
	# Join Geometry
	join_geometry = nodes.new(type="GeometryNodeJoinGeometry")
	join_geometry.location = (200, 0)

	transform.inputs['Scale'].default_value = scale
	transform.inputs['Translation'].default_value = offset
	transform.inputs['Rotation'].default_value = (math.radians(rotation[0]), math.radians(rotation[1]), math.radians(rotation[2]))

	# Connect nodes
	links.new(geomesh.outputs[0], transform.inputs[0])
	links.new(transform.outputs[0], point_instance.inputs['Instance'])
	links.new(group_input.outputs[0], point_instance.inputs[0])
	links.new(group_input.outputs[0], join_geometry.inputs[0])
	links.new(point_instance.outputs[0], join_geometry.inputs[0])
	links.new(join_geometry.outputs[0], group_output.inputs[0])


	return node_group
