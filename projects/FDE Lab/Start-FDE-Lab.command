#!/bin/sh
FDE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$FDE_ROOT/fde" shell
