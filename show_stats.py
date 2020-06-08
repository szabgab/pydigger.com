from PyDigger.common import get_stats, get_latests
stats = get_stats()
for field in sorted(stats.keys()):
    print(f"{stats[field]:7} {field}")

print()
stats = get_latests()
for field in sorted(stats.keys()):
    print(f"{stats[field]:7} {field}")
