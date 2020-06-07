import sys
from PyDigger.common import get_stats
stats = get_stats()
for field in sorted(stats.keys()):
    print(f"{stats[field]:7} {field}")
