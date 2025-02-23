# SPDX-License-Identifier: GPL-2.0-or-later

# ./blender.bin --background -noaudio --python tests/python/bl_pyapi_idprop_datablock.py -- --verbose

import contextlib
import inspect
import io
import os
import re
import sys
import tempfile

import bpy

from bpy.types import UIList

arr_len = 100
ob_cp_count = 100

# Set before execution.
lib_path = None
test_path = None


def print_fail_msg_and_exit(msg):
    def __LINE__():
        try:
            raise Exception
        except:
            return sys.exc_info()[2].tb_frame.f_back.f_back.f_back.f_lineno

    def __FILE__():
        return inspect.currentframe().f_code.co_filename

    print("'%s': %d >> %s" % (__FILE__(), __LINE__(), msg), file=sys.stderr)
    sys.stderr.flush()
    sys.stdout.flush()
    os._exit(1)


def expect_false_or_abort(expr, msg=None):
    if not expr:
        if not msg:
            msg = "test failed"
        print_fail_msg_and_exit(msg)


def expect_exception_or_abort(*, fn, ex):
    try:
        fn()
        exception = False
    except ex:
        exception = True
    if exception:
        return  # OK
    print_fail_msg_and_exit("test failed")


def expect_output_or_abort(*, fn, match_stderr=None, match_stdout=None):
    stdout, stderr = io.StringIO(), io.StringIO()

    with (contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout)):
        fn()

    for (handle, match) in ((stdout, match_stdout), (stderr, match_stderr)):
        if not match:
            continue
        handle.seek(0)
        output = handle.read()
        if not re.match(match, output):
            print_fail_msg_and_exit("%r not found in %r" % (match, output))


class TestClass(bpy.types.PropertyGroup):
    test_prop: bpy.props.PointerProperty(type=bpy.types.Object)
    name: bpy.props.StringProperty()


def get_scene(lib_name, sce_name):
    for s in bpy.data.scenes:
        if s.name == sce_name:
            if (
                    (s.library and s.library.name == lib_name) or
                    (lib_name is None and s.library is None)
            ):
                return s


def init():
    bpy.utils.register_class(TestClass)
    bpy.types.Object.prop_array = bpy.props.CollectionProperty(
        name="prop_array",
        type=TestClass)
    bpy.types.Object.prop = bpy.props.PointerProperty(type=bpy.types.Object)


def make_lib():
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # datablock pointer to an object
    first_object = bpy.data.objects.new("First Object", None)
    bpy.context.collection.objects.link(first_object)

    second_object = bpy.data.objects.new("Second Object", None)
    bpy.context.collection.objects.link(second_object)

    first_object.prop = second_object

    # array of datablock pointers to an object
    third_object = bpy.data.objects.new("Third Object", None)
    bpy.context.collection.objects.link(third_object)
    for i in range(0, arr_len):
        a = first_object.prop_array.add()
        a.test_prop = third_object
        a.name = a.test_prop.name

    # make unique named copy of an object
    ob = first_object.copy()
    bpy.context.collection.objects.link(ob)

    ob.name = "Unique Object"

    # duplicating of object
    for i in range(0, ob_cp_count):
        ob = first_object.copy()
        bpy.context.collection.objects.link(ob)

    # nodes
    bpy.data.scenes["Scene"].use_nodes = True
    bpy.data.scenes["Scene"].node_tree.nodes['Render Layers']["prop"] = \
        third_object

    # rename scene and save
    bpy.data.scenes["Scene"].name = "Scene_lib"
    bpy.ops.wm.save_as_mainfile(filepath=lib_path)


def check_lib():
    # check pointer
    expect_false_or_abort(bpy.data.objects["First Object"].prop == bpy.data.objects["Second Object"])

    # check array of pointers in duplicated object
    for i in range(0, arr_len):
        expect_false_or_abort(
            bpy.data.objects["First Object.001"].prop_array[i].test_prop ==
            bpy.data.objects["Third Object"])


def check_lib_linking():
    # open startup file
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # link scene to the startup file
    with bpy.data.libraries.load(lib_path, link=True) as (data_from, data_to):
        data_to.scenes = ["Scene_lib"]

    o = bpy.data.scenes["Scene_lib"].objects['Unique Object']

    expect_false_or_abort(o.prop_array[0].test_prop == bpy.data.scenes["Scene_lib"].objects['Third Object'])
    expect_false_or_abort(o.prop == bpy.data.scenes["Scene_lib"].objects["Second Object"])
    expect_false_or_abort(o.prop.library == o.library)

    bpy.ops.wm.save_as_mainfile(filepath=test_path)


def check_linked_scene_copying():
    # full copy of the scene with datablock props
    bpy.ops.wm.open_mainfile(filepath=test_path)
    bpy.context.window.scene = bpy.data.scenes["Scene_lib"]
    bpy.ops.scene.new(type='FULL_COPY')

    # check save/open
    bpy.ops.wm.save_as_mainfile(filepath=test_path)
    bpy.ops.wm.open_mainfile(filepath=test_path)

    intern_sce = get_scene(None, "Scene_lib")
    extern_sce = get_scene("lib.blend", "Scene_lib")

    # check node's props
    # must point to own node id proeprty
    expect_false_or_abort(
        intern_sce.node_tree.nodes['Render Layers']["prop"] and
        not (intern_sce.node_tree.nodes['Render Layers']["prop"] ==
             extern_sce.node_tree.nodes['Render Layers']["prop"]))


def check_scene_copying():
    # full copy of the scene with datablock props
    bpy.ops.wm.open_mainfile(filepath=lib_path)
    bpy.context.window.scene = bpy.data.scenes["Scene_lib"]
    bpy.ops.scene.new(type='FULL_COPY')

    path = test_path + "_"
    # check save/open
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)

    first_sce = get_scene(None, "Scene_lib")
    second_sce = get_scene(None, "Scene_lib.001")

    # check node's props
    # must point to own node id property
    expect_false_or_abort(
        not (first_sce.node_tree.nodes['Render Layers']["prop"] ==
             second_sce.node_tree.nodes['Render Layers']["prop"]))


# count users
def test_users_counting():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj = bpy.data.objects.new("", None)
    obj_users = obj.users
    n = 1000
    another_obj = bpy.data.objects.new("", None)
    for i in range(0, n):
        another_obj["a%s" % i] = obj
    expect_false_or_abort(obj.users == obj_users + n)

    for i in range(0, int(n / 2)):
        another_obj["a%s" % i] = 1
    expect_false_or_abort(obj.users == obj_users + int(n / 2))


# linking
def test_linking():
    make_lib()
    check_lib()
    check_lib_linking()
    check_linked_scene_copying()
    check_scene_copying()


# check restrictions for datablock pointers for some classes; GUI for manual testing
def test_restrictions1():
    class TEST_Op(bpy.types.Operator):
        bl_idname = 'scene.test_op'
        bl_label = 'Test'
        bl_options = {"INTERNAL"}

        str_prop: bpy.props.StringProperty(name="str_prop")

        # disallow registration of datablock properties in operators
        # will be checked in the draw method (test manually)
        # also, see console:
        #   ValueError: bpy_struct "SCENE_OT_test_op" doesn't support datablock properties
        id_prop: bpy.props.PointerProperty(type=bpy.types.Object)

        def execute(self, context):
            return {'FINISHED'}

    # just panel for testing the poll callback with lots of objects
    class TEST_PT_DatablockProp(bpy.types.Panel):
        bl_label = "Datablock IDProp"
        bl_space_type = 'PROPERTIES'
        bl_region_type = 'WINDOW'
        bl_context = "render"

        def draw(self, context):
            self.layout.prop_search(context.scene, "prop", bpy.data, "objects")
            self.layout.template_ID(context.scene, "prop1")
            self.layout.prop_search(context.scene, "prop2", bpy.data, "node_groups")

            op = self.layout.operator(TEST_Op.bl_idname)
            op.str_prop = "test string"

            def test_fn(op):
                op["ob"] = bpy.data.objects['Unique Object']

            expect_exception_or_abort(
                fn=lambda: test_fn(op),
                ex=ImportError,
            )
            expect_false_or_abort(not hasattr(op, "id_prop"))

    bpy.utils.register_class(TEST_PT_DatablockProp)
    expect_output_or_abort(
        fn=lambda: bpy.utils.register_class(TEST_Op),
        match_stderr="^ValueError: bpy_struct \"SCENE_OT_test_op\" registration error:",
    )

    def poll(self, value):
        return value.name in bpy.data.scenes["Scene_lib"].objects

    def poll1(self, value):
        return True

    bpy.types.Scene.prop = bpy.props.PointerProperty(type=bpy.types.Object)
    bpy.types.Scene.prop1 = bpy.props.PointerProperty(type=bpy.types.Object, poll=poll)
    bpy.types.Scene.prop2 = bpy.props.PointerProperty(type=bpy.types.NodeTree, poll=poll1)

    # check poll effect on UI (poll returns false => red alert)
    bpy.context.scene.prop = bpy.data.objects["Third Object"]
    bpy.context.scene.prop1 = bpy.data.objects["Third Object"]

    # check incorrect type assignment
    def sub_test():
        # NodeTree id_prop
        bpy.context.scene.prop2 = bpy.data.objects["Third Object"]

    expect_exception_or_abort(
        fn=sub_test,
        ex=TypeError,
    )

    bpy.context.scene.prop2 = bpy.data.node_groups.new("Shader", "ShaderNodeTree")

    # NOTE: keep since the author thought this useful information.
    # print(
    #     "Please, test GUI performance manually on the Render tab, '%s' panel" %
    #     TEST_PT_DatablockProp.bl_label, file=sys.stderr,
    # )
    sys.stderr.flush()


# check some possible regressions
def test_regressions():
    bpy.types.Object.prop_str = bpy.props.StringProperty(name="str")
    bpy.data.objects["Unique Object"].prop_str = "test"

    bpy.types.Object.prop_gr = bpy.props.PointerProperty(
        name="prop_gr",
        type=TestClass,
        description="test")

    bpy.data.objects["Unique Object"].prop_gr = None


# test restrictions for datablock pointers
def test_restrictions2():
    class TestClassCollection(bpy.types.PropertyGroup):
        prop: bpy.props.CollectionProperty(
            name="prop_array",
            type=TestClass)

    bpy.utils.register_class(TestClassCollection)

    class TestPrefs(bpy.types.AddonPreferences):
        bl_idname = "testprefs"
        # expecting crash during registering
        my_prop2: bpy.props.PointerProperty(type=TestClass)

        prop: bpy.props.PointerProperty(
            name="prop",
            type=TestClassCollection,
            description="test")

    bpy.types.Addon.a = bpy.props.PointerProperty(type=bpy.types.Object)

    class TEST_UL_list(UIList):
        test: bpy.props.PointerProperty(type=bpy.types.Object)

        def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
            layout.prop(item, "name", text="", emboss=False, icon_value=icon)

    expect_exception_or_abort(
        fn=lambda: bpy.utils.register_class(TestPrefs),
        ex=ValueError,
    )
    expect_exception_or_abort(
        fn=lambda: bpy.utils.register_class(TEST_UL_list),
        ex=ValueError,
    )

    bpy.utils.unregister_class(TestClassCollection)


def main():
    global lib_path
    global test_path
    with tempfile.TemporaryDirectory() as temp_dir:
        lib_path = os.path.join(temp_dir, "lib.blend")
        test_path = os.path.join(temp_dir, "test.blend")

        init()
        test_users_counting()
        test_linking()
        test_restrictions1()
        expect_exception_or_abort(
            fn=test_regressions,
            ex=AttributeError,
        )
        test_restrictions2()


if __name__ == "__main__":
    main()
