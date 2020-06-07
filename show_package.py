import sys
from PyDigger.common import show_package
if len(sys.argv) != 2:
    exit("Usage: {} NAME-OF-THE-PAKAGE")
show_package(sys.argv[1])
