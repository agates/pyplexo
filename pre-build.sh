#!/bin/sh


# Remove build artifacts from previous version
# Otherwise we get multiple version .so files, creating large wheels
find ./ -type f \( -iname '*.so' -o -iname '*.pyx' -o -iname '*.c' \) -delete
rm -rf build