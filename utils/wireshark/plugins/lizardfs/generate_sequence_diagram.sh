#!/usr/bin/env bash
me=$(basename -s .sh $0)

declare -A tokens
tokens[AN]=ANY
tokens[CL]=CLIENT
tokens[CS]=CHUNKSERVER
tokens[MA]=MASTER
tokens[ML]=METALOGGER
tokens[TS]=TAPESERVER
declare -a sorted_keys=(CL MA CS ML TS AN)

usage(){
  echo -e "\nUsage: ${me} path/to/MFSCommunication.h\n" > /dev/stderr
  exit 1
}

source_file="${1:-}"
[ -z "${source_file}" ] && usage

echo "title LizardFS Protocol"
echo
for key in "${sorted_keys[@]}"; do
  echo "participant ${tokens[$key]}"
done
echo

get_key_disjunction() {
  local key_list="${!tokens[@]}"
  echo "${key_list}" | tr ' ' '|'
}

get_search_pattern() {
  ored_keys="$(get_key_disjunction)"
  echo '('"${ored_keys}"')TO('"${ored_keys}"')'
}

get_transformation_pattern() {
  search_pattern="$(get_search_pattern)"
  echo 's/(LIZ_)?'"${search_pattern}"'/\2->\3:\0/;'
  local key_list="${!tokens[@]}"
  for key in ${key_list}; do
    echo 's/(^|>)'"${key}"'/\1'"${tokens[${key}]}"'/g;'
  done
}

search_pattern="$(get_search_pattern)"
transform_pattern="$(get_transformation_pattern)"
cat "${source_file}" \
  | egrep -o '#define\s+\w+' \
  | awk '{print $2}' \
  | egrep "${search_pattern}" \
  | sed -E "${transform_pattern}"
