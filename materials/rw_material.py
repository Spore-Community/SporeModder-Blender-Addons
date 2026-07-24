__author__ = 'Eric'


import bpy
from .. import rw4_enums
from bpy.props import BoolProperty


# All RW materials must extend this class
class RWMaterial(bpy.types.PropertyGroup):
	material_name = ""
	material_description = ""
	material_has_material_color = False
	material_has_ambient_color = False
	material_use_alpha = False

	@staticmethod
	def set_pointer_property(cls):
		pass

	@staticmethod
	def get_material_data(rw4_material):
		return None

	@staticmethod
	def draw_panel(layout, rw4_material):
		pass

	@staticmethod
	def get_material_builder(exporter, rw4_material):
		return None

	@staticmethod
	def parse_material_builder(material, rw4_material):
		# parse the basic things
		
		if material.material_color is not None:
			rw4_material.material_color = material.material_color
		
		if material.ambient_color is not None:
			rw4_material.ambient_color = material.ambient_color
		
		rw4_material.alpha_type = material.detect_render_states()

		# Autofill the custom render states into the rw4_material's properties
		for variable_name in dir(rw4_material):
			if not variable_name.startswith('renderstate_'):
				continue

			state_name = variable_name[len('renderstate_'):].upper()
			state_enum_name = 'D3DRS_' + state_name
			if not hasattr(rw4_enums, state_enum_name):
				continue

			render_state = getattr(rw4_enums, state_enum_name)
			if render_state in material.render_states:
				value = material.render_states[render_state]

				property_def = rw4_material.bl_rna.properties.get(variable_name)
				if property_def is not None and property_def.type == 'ENUM':
					value = str(value)

				setattr(rw4_material, variable_name, value)
		
		return False  # return True if the material was of the specified type

	@staticmethod
	def set_general_settings(material_builder, rw4_material, material_data):

		if material_data.material_has_material_color:
			material_builder.material_color = rw4_material.material_color

		if material_data.material_has_ambient_color:
			material_builder.ambient_color = rw4_material.ambient_color
			
		if material_data.material_use_alpha:
			if rw4_material.alpha_type != 'CUSTOM':
				material_builder.set_render_states(rw4_material.alpha_type)
			else:
				for variable_name in dir(rw4_material):
					if not variable_name.startswith('renderstate_'):
						continue

					state_name = variable_name[len('renderstate_'):].upper()
					state_enum_name = 'D3DRS_' + state_name
					if not hasattr(rw4_enums, state_enum_name):
						continue

					render_state = getattr(rw4_enums, state_enum_name)
					value = getattr(rw4_material, variable_name)

					if isinstance(value, str):
						property_def = rw4_material.bl_rna.properties.get(variable_name)
						if property_def is not None and property_def.type == 'ENUM':
							try:
								value = int(value)
							except ValueError:
								if hasattr(rw4_enums, value):
									value = getattr(rw4_enums, value)
						elif hasattr(rw4_enums, value):
							value = getattr(rw4_enums, value)

					material_builder.set_render_state(render_state, value)

	@staticmethod
	def set_texture(obj, material, slot_index, path):
		pass
