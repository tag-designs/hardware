# Record which layout a set of renders was drawn from.
#
# Invoked as a script: cmake -DBOARD=<path> -DSTAMP=<path> -P stamp.cmake
#
# A separate script rather than a redirected `cmake -E sha256sum` because
# add_custom_command(VERBATIM) passes ">" through as an argument instead of
# treating it as a shell redirection.

if(NOT DEFINED BOARD OR NOT DEFINED STAMP)
  message(FATAL_ERROR "stamp.cmake needs -DBOARD= and -DSTAMP=")
endif()

file(SHA256 "${BOARD}" _hash)
get_filename_component(_name "${BOARD}" NAME)
file(WRITE "${STAMP}" "${_hash}  ${_name}\n")
