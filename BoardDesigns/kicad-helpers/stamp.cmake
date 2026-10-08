# Record which source files an output was generated from.
#
# Invoked as a script, with one path or a list of them:
#   cmake -DBOARD=<pcb> -DSTAMP=<out> -P stamp.cmake
#   cmake "-DBOARD=<sheet>;<sheet>" -DSTAMP=<out> -P stamp.cmake
#
# Writes one "<sha256>  <filename>" line per source, sorted by filename so the
# file does not churn when a glob comes back in a different order.
#
# A separate script rather than a redirected `cmake -E sha256sum` because
# add_custom_command(VERBATIM) passes ">" through as an argument instead of
# treating it as a shell redirection.

if(NOT DEFINED BOARD OR NOT DEFINED STAMP)
  message(FATAL_ERROR "stamp.cmake needs -DBOARD= and -DSTAMP=")
endif()

# Sorted by file name, not by the composed line, so a changed hash cannot
# reorder the file.
set(_sources ${BOARD})
list(SORT _sources COMPARE FILE_BASENAME ORDER ASCENDING)

set(_lines "")
foreach(_src IN LISTS _sources)
  if(NOT EXISTS "${_src}")
    message(FATAL_ERROR "stamp.cmake: no such file: ${_src}")
  endif()
  file(SHA256 "${_src}" _hash)
  get_filename_component(_name "${_src}" NAME)
  list(APPEND _lines "${_hash}  ${_name}")
endforeach()

list(JOIN _lines "\n" _text)
file(WRITE "${STAMP}" "${_text}\n")
