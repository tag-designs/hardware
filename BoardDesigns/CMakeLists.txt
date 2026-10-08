cmake_minimum_required(VERSION 3.15)

# Two separate jobs live in this file.
#
# Documentation renders are the one the default build cares about. They are
# made with kicad-cli, which ships inside KiCad itself, so producing pictures
# of a board needs nothing installed beyond KiCad. They are written into the
# documentation tree and committed, because the docs workflow that publishes
# the site installs Python and MkDocs only -- it has no KiCad to render with.
#
# Fabrication outputs -- gerbers, drill, DXF, BOM, STEP, schematic PDF -- are
# made with KiBot, which is an external tool. They are opt-in: each board gets
# a <board>-pcb target that is never part of the default build, so an ordinary
# build neither needs KiBot nor shells out to it. Run one when you are actually
# sending a board out.

find_program(kibot_EXECUTABLE kibot
             HINTS /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.8/bin/
             NO_CACHE)

find_program(kicad_cli_EXECUTABLE kicad-cli
             HINTS /Applications/KiCad/KiCad.app/Contents/MacOS/
             NO_CACHE)

# Renders are committed, so they belong in the source tree, not the build tree.
get_filename_component(_hw_root "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)
set(BOARD_RENDER_DIR "${_hw_root}/docs/src/images/boards")

# Aggregate target: "cmake --build . --target board-renders" redraws every
# board whose .kicad_pcb has changed since its images were written. Deliberately
# not part of ALL -- a normal build should not rewrite files under version
# control.
add_custom_target(board-renders
  COMMENT "Board renders for the documentation")

# Top and bottom renders for one board, regenerated when its layout changes.
function(add_board_renders name)
  if(NOT kicad_cli_EXECUTABLE)
    return()
  endif()

  set(board "${CMAKE_CURRENT_SOURCE_DIR}/${name}.kicad_pcb")
  set(outputs "")

  foreach(side top bottom)
    set(out "${BOARD_RENDER_DIR}/${name}-${side}.png")
    add_custom_command(
      OUTPUT "${out}"
      COMMAND ${CMAKE_COMMAND} -E make_directory "${BOARD_RENDER_DIR}"
      # --background transparent so one image reads correctly against both the
      # light and dark documentation themes. Long option names throughout:
      # kicad-cli's short -h means height, not help.
      COMMAND ${kicad_cli_EXECUTABLE} pcb render
              --side ${side}
              --quality high
              --width 1600
              --height 1200
              --background transparent
              --output "${out}"
              "${board}"
      DEPENDS "${board}"
      COMMENT "Rendering ${name} (${side})"
      VERBATIM)
    list(APPEND outputs "${out}")
  endforeach()

  add_custom_target(${name}-renders DEPENDS ${outputs})
  add_dependencies(board-renders ${name}-renders)
endfunction()

function (add_pcb_outputs name)

  # Fabrication outputs need KiBot. Without it the board still configures and
  # still renders; only this target is skipped.
  if(NOT kibot_EXECUTABLE)
    return()
  endif()

  # see if there's an extra argument (builddir)

  set(ExtraArgs ${ARGN})

  # Get the length of the args list

  list(LENGTH ExtraArgs NumExtraArgs)

  # Set the build directory

  if(NumExtraArgs GREATER 0)
    list(GET ExtraArgs 0 builddir)
  else()
    set(builddir ${CMAKE_CURRENT_BINARY_DIR})
  endif()
    set(stampfile ${builddir}/pcb.stamp)

  add_custom_command(OUTPUT ${stampfile}
             COMMAND ${kibot_EXECUTABLE} -d ${builddir}
             COMMAND ${CMAKE_COMMAND} -E touch ${stampfile}
             WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
             DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/${name}.kibot.yaml" "${CMAKE_CURRENT_SOURCE_DIR}/${name}.kicad_sch"  "${CMAKE_CURRENT_SOURCE_DIR}/${name}.kicad_pcb"
             COMMENT "Building ${name}")

    add_custom_target(${name}-pcb DEPENDS ${stampfile} )

endfunction()

message("Configure PCBs")
# add_subdirectory(AccelTag)
#add_subdirectory(BitTagv5)
add_subdirectory(Tags/BitTagv7)
add_subdirectory(Tags/BitTagNG)
add_subdirectory(Tags/CompassTag)
add_subdirectory(Chargers/MultiCharger)
add_subdirectory(Tags/PresTag-v6)
add_subdirectory(Tags/imutag-smps)
add_subdirectory(Tags/BitPresTagBMP585)
# add_subdirectory(PresTagBMP581)  # no such board (Obsolete/ or never existed)
add_subdirectory(Prototypes/steval-daughter-v2)
add_subdirectory(Bases/tag-breakout-v2)
# add_subdirectory(tagbase-jlcpcb-v3)  # no such board (Obsolete/ or never existed)
add_subdirectory(Bases/tagbase-v7)
add_subdirectory(Prototypes/TagMagAccelPresBreakout)
add_subdirectory(Prototypes/BitPresTagBreakout)
add_subdirectory(Prototypes/CompassTagBreakout)
add_subdirectory(Bases/tag-breakout-l432v1)
add_subdirectory(Bases/nucleoshield-c071-base-test)

if(NOT kicad_cli_EXECUTABLE)
    message(STATUS "kicad-cli not found -- board renders cannot be regenerated")
endif()
if(NOT kibot_EXECUTABLE)
    message(STATUS "kibot not found -- fabrication outputs are unavailable")
endif()

# add_subdirectory(Mechanical)  # no such board (Obsolete/ or never existed)


