import sys
from PyDigger.common import remove_package
if len(sys.argv) != 2:
    exit("Usage: {} NAME-OF-THE-PAKAGE")
remove_package(sys.argv[1])
