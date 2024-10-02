#!/bin/bash

rurl="$1" localdir="$2" && shift 2

mkdir -p "$localdir"
cd "$localdir"

git init
git remote add -f origin "$rurl"

git config core.sparseCheckout true

for i; do
echo "$i" >> .git/info/sparse-checkout
done

git pull origin master
