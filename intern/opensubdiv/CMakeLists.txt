# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright 2013 Blender Foundation. All rights reserved.

set(INC
  .
  ../guardedalloc
)

set(INC_SYS
)

set(SRC
  opensubdiv_capi.h
  opensubdiv_capi_type.h
  opensubdiv_converter_capi.h
  opensubdiv_evaluator_capi.h
  opensubdiv_topology_refiner_capi.h
)

set(LIB
)

if(WITH_OPENSUBDIV)
  macro(OPENSUBDIV_DEFINE_COMPONENT component)
    if(${${component}})
      add_definitions(-D${component})
    endif()
  endmacro()

  list(APPEND INC_SYS
    ${OPENSUBDIV_INCLUDE_DIRS}
    ${Epoxy_INCLUDE_DIRS}
  )

  list(APPEND SRC
    # Base.
    internal/base/memory.h
    internal/base/opensubdiv_capi.cc
    internal/base/type.h
    internal/base/type_convert.cc
    internal/base/type_convert.h
    internal/base/util.cc
    internal/base/util.h

    # Evaluator.
    internal/evaluator/eval_output.cc
    internal/evaluator/eval_output.h
    internal/evaluator/eval_output_cpu.cc
    internal/evaluator/eval_output_cpu.h
    internal/evaluator/eval_output_gpu.cc
    internal/evaluator/eval_output_gpu.h
    internal/evaluator/evaluator_cache_impl.cc
    internal/evaluator/evaluator_cache_impl.h
    internal/evaluator/evaluator_capi.cc
    internal/evaluator/evaluator_impl.cc
    internal/evaluator/evaluator_impl.h
    internal/evaluator/gl_compute_evaluator.cc
    internal/evaluator/gl_compute_evaluator.h
    internal/evaluator/patch_map.cc
    internal/evaluator/patch_map.h


    # Topology.
    internal/topology/mesh_topology.cc
    internal/topology/mesh_topology_compare.cc
    internal/topology/mesh_topology.h
    internal/topology/topology_refiner_capi.cc
    internal/topology/topology_refiner_factory.cc
    internal/topology/topology_refiner_impl.cc
    internal/topology/topology_refiner_impl_compare.cc
    internal/topology/topology_refiner_impl.h
  )

  list(APPEND LIB
    ${OPENSUBDIV_LIBRARIES}
  )

  if(WITH_OPENMP_STATIC)
    list(APPEND LIB
      ${OpenMP_LIBRARIES}
    )
  endif()

  OPENSUBDIV_DEFINE_COMPONENT(OPENSUBDIV_HAS_OPENMP)
  OPENSUBDIV_DEFINE_COMPONENT(OPENSUBDIV_HAS_OPENCL)
  OPENSUBDIV_DEFINE_COMPONENT(OPENSUBDIV_HAS_CUDA)
  OPENSUBDIV_DEFINE_COMPONENT(OPENSUBDIV_HAS_GLSL_TRANSFORM_FEEDBACK)
  OPENSUBDIV_DEFINE_COMPONENT(OPENSUBDIV_HAS_GLSL_COMPUTE)

  if(WIN32)
    add_definitions(-DNOMINMAX)
    add_definitions(-D_USE_MATH_DEFINES)
  endif()

  data_to_c_simple(internal/evaluator/shaders/glsl_compute_kernel.glsl SRC)
else()
  list(APPEND SRC
    stub/opensubdiv_stub.cc
    stub/opensubdiv_evaluator_stub.cc
    stub/opensubdiv_topology_refiner_stub.cc
  )
endif()

blender_add_lib(bf_intern_opensubdiv "${SRC}" "${INC}" "${INC_SYS}" "${LIB}")

# Tests.

if(WITH_GTESTS AND WITH_OPENSUBDIV)
  include(GTestTesting)

  add_definitions(${GFLAGS_DEFINES})
  add_definitions(${GLOG_DEFINES})

  blender_add_test_executable(opensubdiv_mesh_topology_test "internal/topology/mesh_topology_test.cc" "${INC}" "${INC_SYS}" "${LIB};bf_intern_opensubdiv")
endif()
