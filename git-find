#!/bin/bash

#
# Small utility script that recursively searches for git repositories in files
# and displays their states (up-to date or the pending diffs)
# 
# Usage: git-find [<path>] [-q|--quiet]
#

quiet=0
search_dir="."

for var in "$@"
do
  if [[ $var = "-q" ]] || [[ $var = "--quiet" ]]; then
    quiet=1
  elif [[ $var = \-* ]] || [[ $search_dir != "." ]]; then
    echo "Usage: $0 [-q] [<search_path>]"
    exit
  else
    search_dir=$var
  fi
done

find "$search_dir" -type d -name .git 2> /dev/null | while read dotgit
do
  repo_path=${dotgit::-4}
  if [[ $quiet -eq 0 ]]; then
    echo -e "Found repository at \033[1;32m$repo_path\033[0m"
    git -C "$repo_path" status -s
    [[ ! -z $(git -C "$repo_path" status -s) ]] || echo " Up-to date"
  else
    echo $repo_path
  fi
done

