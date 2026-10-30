#!/bin/sh
cd -- "$(dirname -- "$0")" || exit 1
sh ./install.sh
result=$?
printf '\nPress Enter to close this window.'
read -r answer
exit "$result"
