#!/bin/bash
MYDIR="$(dirname "$(readlink -f "$0")")"
cd $MYDIR/src
python interface.py
