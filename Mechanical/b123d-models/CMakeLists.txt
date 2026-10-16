cmake_minimum_required(VERSION 3.15)

# Tag cases built with build123d from the board files (experimental; see
# README.md). Configure on its own --
#     cmake -S Mechanical/b123d-models -B build-tagcases
#     cmake --build build-tagcases --target tagcases
# -- or from the top level, where Mechanical/CMakeLists.txt includes it. NONE
# because nothing is compiled.
project(TagCases NONE)

# Experimental, and it needs a Python environment most checkouts will not
# have, so a top-level configure can opt out rather than fail.
option(TAGCASES "Build the experimental build123d tag cases" ON)
if(NOT TAGCASES)
  message(STATUS "Tag cases (build123d): skipped, TAGCASES=OFF")
  return()
endif()

# The interpreter with build123d in it. Not find_package(Python3): from the top
# level that would share Python3_EXECUTABLE with BoardDesigns, which wants the
# one with Pillow. Override with -DTAGCASE_PYTHON=/path/to/python.
if(NOT DEFINED TAGCASE_PYTHON)
  set(TAGCASE_PYTHON "$ENV{HOME}/cq-env/bin/python")
endif()

# Hard errors, as in BoardDesigns: a configure that quietly made no targets
# would let a build "succeed" without producing anything.
execute_process(COMMAND "${TAGCASE_PYTHON}" -c "import build123d, fontTools, pyvista"
                RESULT_VARIABLE _py OUTPUT_QUIET ERROR_QUIET)
if(NOT _py EQUAL 0)
  message(FATAL_ERROR
    "No Python with build123d, fontTools and pyvista at ${TAGCASE_PYTHON}. "
    "Install requirements.txt there, point at another interpreter with "
    "-DTAGCASE_PYTHON=..., or skip these cases with -DTAGCASES=OFF.")
endif()

# kicad-cli exports each board in 3D: part heights for the lids come from it,
# so the parts cannot be built without it, not only checked.
find_program(tagcase_kicad_cli kicad-cli
             HINTS /Applications/KiCad/KiCad.app/Contents/MacOS/
             NO_CACHE)
if(NOT tagcase_kicad_cli)
  message(FATAL_ERROR
    "kicad-cli not found; the tag cases need it for each board's 3D export. "
    "Skip them with -DTAGCASES=OFF.")
endif()

# The cases, from cases/build.py, so adding one stays a one-line edit there.
# Re-read whenever that file changes.
execute_process(COMMAND "${TAGCASE_PYTHON}" -m cases.build --list
                WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
                OUTPUT_VARIABLE _list RESULT_VARIABLE _rc ERROR_VARIABLE _err)
if(NOT _rc EQUAL 0)
  message(FATAL_ERROR "cases/build.py --list failed:\n${_err}")
endif()
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
             "${CMAKE_CURRENT_SOURCE_DIR}/cases/build.py")

# Every case depends on the whole library, and on the build/render scripts.
file(GLOB _library CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/tagcase/*.py")
list(APPEND _library "${CMAKE_CURRENT_SOURCE_DIR}/cases/build.py")

# Output goes to the build tree: nothing here is committed. When a case is
# printed, its STLs are copied into that tag's case folder by hand.
set(TAGCASE_OUT "${CMAKE_CURRENT_BINARY_DIR}/out")

# Not part of ALL: a full run takes about a minute and needs KiCad.
#   tagcases          build and fit-check every case
#   tagcase-<Name>    one case
#   tagcase-renders   PNGs of every case's parts and fit
add_custom_target(tagcases COMMENT "Tag cases (build123d)")
add_custom_target(tagcase-renders COMMENT "Tag case renders")

string(REPLACE "\n" ";" _lines "${_list}")
set(_names "")
foreach(_line IN LISTS _lines)
  if(_line STREQUAL "")
    continue()
  endif()
  string(REPLACE "\t" ";" _f "${_line}")
  list(GET _f 0 name)
  list(GET _f 1 board)
  list(APPEND _names "${name}")

  # The declared output is a marker, touched only after the fit check passes:
  # a case that fails stays out of date and is rebuilt (and re-reported) next
  # time, instead of leaving parts that look current.
  set(done "${TAGCASE_OUT}/${name}.done")
  set(parts "")
  foreach(p base lid lid-nobattery)
    list(APPEND parts "${TAGCASE_OUT}/${name}-${p}.stl" "${TAGCASE_OUT}/${name}-${p}.step")
  endforeach()
  add_custom_command(
    OUTPUT "${done}"
    BYPRODUCTS ${parts} "${TAGCASE_OUT}/${name}-assembly.step"
    COMMAND ${CMAKE_COMMAND} -E rm -f "${done}"
    COMMAND "${TAGCASE_PYTHON}" -m cases.build --out "${TAGCASE_OUT}" "${name}"
    COMMAND ${CMAKE_COMMAND} -E touch "${done}"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    DEPENDS "${board}" ${_library}
    COMMENT "Tag case ${name}: parts and fit check"
    VERBATIM)
  add_custom_target(tagcase-${name} DEPENDS "${done}")
  add_dependencies(tagcases tagcase-${name})

  set(rendered "${TAGCASE_OUT}/${name}.rendered")
  add_custom_command(
    OUTPUT "${rendered}"
    COMMAND "${TAGCASE_PYTHON}" render.py --out "${TAGCASE_OUT}" "${name}"
    COMMAND ${CMAKE_COMMAND} -E touch "${rendered}"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    DEPENDS "${done}" "${CMAKE_CURRENT_SOURCE_DIR}/render.py"
    COMMENT "Tag case ${name}: renders"
    VERBATIM)
  add_custom_target(tagcase-${name}-render DEPENDS "${rendered}")
  add_dependencies(tagcase-renders tagcase-${name}-render)
endforeach()

message(STATUS "Tag cases (build123d): ${_names} -> ${TAGCASE_OUT}")
