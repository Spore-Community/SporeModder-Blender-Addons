__author__ = 'Eric'

import bpy
from bpy.props import (StringProperty,
					   FloatVectorProperty,
					   EnumProperty,
					   BoolProperty,
					   IntProperty,
					   PointerProperty,
					   )

from . import rw4_enums
from . import materials, addon_updater_ops
from collections import namedtuple


ActiveMaterial = namedtuple('ActiveMaterial', ('material_data', 'material_class'))


def set_material_type(rw4_material, context):
	for cls in materials.material_classes:
		print(cls.__name__)
		cls.set_is_active_material(rw4_material, cls.__name__ == rw4_material.material_type)

	return None


def parse_material_builder(material_builder, rw4_material):
	for cls in materials.material_classes:
		if cls.parse_material_builder(material_builder, rw4_material):
			rw4_material.material_type = cls.__name__
			break


def get_active_material(rw4_material):
	for cls in materials.material_classes:
		if cls.__name__ == rw4_material.material_type:
			return ActiveMaterial(cls.get_material_data(rw4_material), cls)

	return None


materials_enum = [(cls.__name__, cls.material_name, cls.material_description) for cls in materials.material_classes]


def material_type_getter(self):
	for i in range(len(materials_enum)):
		if materials_enum[i][0] == self.material_type_str:
			return i

	return -1


def material_type_setter(self, value):
	self.material_type_str = materials_enum[value][0]


class RWBaseMaterial(bpy.types.PropertyGroup):
	@classmethod
	def register(cls):
		bpy.types.Material.rw4 = PointerProperty(type=cls)

		cls.material_type = EnumProperty(
			items=materials_enum,
			name="Material Type",
			description="The type of material used by this mesh, determines the shader, textures, etc",
			get=material_type_getter,
			set=material_type_setter,
			default="SkinPaintPart"
		)

		# get_materials_enum() doesn't always return the same order, so we must store a string instead of an int
		cls.material_type_str = StringProperty(
			default="SkinPaintPart"
		)

		cls.material_color = FloatVectorProperty(
			name="Material Color",
			subtype='COLOR',
			default=(1.0, 1.0, 1.0, 1.0),
			min=0.0,
			max=1.0,
			size=4
		)

		cls.ambient_color = FloatVectorProperty(
			name="Ambient Color",
			subtype='COLOR',
			default=(1.0, 1.0, 1.0),
			min=0.0,
			max=1.0,
			size=3
		)

		cls.alpha_type = EnumProperty(
			name="Material Opacity",
			items=[('NO_ALPHA', 'Opaque', "The material has no transparency."),
				   ('ALPHA', "Alpha", "The material can have transparency, determined by the texture's alpha channel."),
				   ('EXCLUDING_ALPHA', "Excluding", "Pixels with transpareny < 127 won't be rendered."),
				   ('CUSTOM', "Custom", "Configure this material's render states manually.")],
			default='NO_ALPHA'
		)

		# CUSTOM ALPHA / RENDER STATES
		register_custom_render_states(cls)

		for clazz in materials.material_classes:
			clazz.set_pointer_property(cls)

	@classmethod
	def unregister(cls):
		del bpy.types.Material.rw4


class SPORE_PT_rw_material(bpy.types.Panel):
	bl_label = "RenderWare4 Material Config"
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = 'material'

	def draw(self, context):
		addon_updater_ops.check_for_update_background()

		if context.material is not None:
			material_data = context.material.rw4

			self.layout.use_property_split = True

			self.layout.prop(material_data, 'material_type')

			active_material = get_active_material(material_data)

			if active_material is not None:

				if active_material.material_data.material_has_material_color:
					self.layout.prop(material_data, 'material_color')

				if active_material.material_data.material_has_ambient_color:
					self.layout.prop(material_data, 'ambient_color')
					
				if active_material.material_data.material_use_alpha:
					self.layout.prop(material_data, 'alpha_type')

				if material_data.alpha_type == 'CUSTOM':
					box = self.layout.box()
					box.label(text="Custom Render States")
					#
					box.prop(material_data, "renderstate_alphablendenable")
					box.prop(material_data, "renderstate_alphatestenable")
					box.prop(material_data, "renderstate_alpharef")
					box.prop(material_data, "renderstate_alphafunc")
					#
					box.prop(material_data, "renderstate_lighting")
					box.prop(material_data, "renderstate_fogenable")
					#
					box.prop(material_data, "renderstate_colorwriteenable")
					box.prop(material_data, "renderstate_zwriteenable")
					box.prop(material_data, "renderstate_zfunc")
					#
					box.prop(material_data, "renderstate_srcblend")
					box.prop(material_data, "renderstate_destblend")

				active_material.material_class.draw_panel(self.layout, material_data)

		addon_updater_ops.update_notice_box_ui(self, context)


def register():
	for cls in materials.material_classes:
		bpy.utils.register_class(cls)

	bpy.utils.register_class(RWBaseMaterial)
	bpy.utils.register_class(SPORE_PT_rw_material)


def unregister():
	for cls in materials.material_classes:
		bpy.utils.unregister_class(cls)

	bpy.utils.unregister_class(RWBaseMaterial)
	bpy.utils.unregister_class(SPORE_PT_rw_material)


# CUSTOM ALPHA / RENDER STATES
def register_custom_render_states(cls):

	cls.renderstate_alphablendenable = BoolProperty(
		name="Alpha Blending",
		description="Enable alpha blending",
		default=True
	)
	cls.renderstate_alphatestenable = BoolProperty(
		name="Alpha Test",
		description="Enable alpha tested transparency. Pixels with alpha < 'Alpha Reference' won't be rendered",
		default=True
	)
	cls.renderstate_alpharef = IntProperty(
		name="Alpha Reference",
		description="The threshold for alpha testing. Pixels with alpha below this value won't be rendered. 'Excluding' default = 127",
		default=0,
		min=0,
		max=255
	)
	cls.renderstate_alphafunc = EnumProperty(
		name="Alpha Function",
		description="Function used for alpha testing",
		items=[
			(str(rw4_enums.D3DCMP_NEVER), "Never", "Never"),
			(str(rw4_enums.D3DCMP_LESS), "Less", "Less"),
			(str(rw4_enums.D3DCMP_EQUAL), "Equal", "Equal"),
			(str(rw4_enums.D3DCMP_LESSEQUAL), "Less Equal", "Less Equal"),
			(str(rw4_enums.D3DCMP_GREATER), "Greater", "Greater"),
			(str(rw4_enums.D3DCMP_NOTEQUAL), "Not Equal", "Not Equal"),
			(str(rw4_enums.D3DCMP_GREATEREQUAL), "Greater Equal", "Greater Equal"),
			(str(rw4_enums.D3DCMP_ALWAYS), "Always", "Always"),
		],
		default=str(rw4_enums.D3DCMP_GREATER)
	)
	cls.renderstate_lighting = BoolProperty(
		name="Enable Lighting",
		description="Enable model lighting",
		default=True
	)
	cls.renderstate_fogenable = BoolProperty(

		name="Enable Fog",
		description="Enable fog rendering",
		default=True
	)
	cls.renderstate_colorwriteenable = EnumProperty(
		name="Color Write",
		description="Enable per-channel color buffer writing",
		items=[
			("0", "Off", "False"),
			("15", "On", "True"),
		],
		default="0"
	)
	cls.renderstate_zwriteenable = BoolProperty(
		name="Enable Z-Write",
		description="Enable depth buffer writing",
		default=True
	)
	cls.renderstate_zfunc = EnumProperty(
		name="Z function",
		description="Function used for Z testing",
		items=[
			(str(rw4_enums.D3DCMP_NEVER), "Never", "Never"),
			(str(rw4_enums.D3DCMP_LESS), "Less", "Less"),
			(str(rw4_enums.D3DCMP_EQUAL), "Equal", "Equal"),
			(str(rw4_enums.D3DCMP_LESSEQUAL), "Less Equal", "Less Equal"),
			(str(rw4_enums.D3DCMP_GREATER), "Greater", "Greater"),
			(str(rw4_enums.D3DCMP_NOTEQUAL), "Not Equal", "Not Equal"),
			(str(rw4_enums.D3DCMP_GREATEREQUAL), "Greater Equal", "Greater Equal"),
			(str(rw4_enums.D3DCMP_ALWAYS), "Always", "Always"),
		],
		default=str(rw4_enums.D3DCMP_LESSEQUAL)
	)
	#----------------------------------------

	cls.renderstate_srcblend = EnumProperty(
		name="Source Alpha",
		description="Source blend mode for alpha blending",
		items=[
			(str(rw4_enums.D3DBLEND_SRCALPHA), "Source Alpha", "Source Alpha"),
			(str(rw4_enums.D3DBLEND_INVSRCALPHA), "Inverse Src Alpha", "Inverse Source Alpha"),
		],
		default=str(rw4_enums.D3DBLEND_SRCALPHA)
	)
	cls.renderstate_destblend = EnumProperty(
		name="Dest Alpha",
		description="Destination blend mode for alpha blending",
		items=[
			(str(rw4_enums.D3DBLEND_SRCALPHA), "Source Alpha", "Source Alpha"),
			(str(rw4_enums.D3DBLEND_INVSRCALPHA), "Inverse Src Alpha", "Inverse Source Alpha"),
		],
		default=str(rw4_enums.D3DBLEND_INVSRCALPHA)
	)