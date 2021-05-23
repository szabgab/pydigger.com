from flake8.api import legacy as flake8
import os
import sys
import re
from io import StringIO

# Given a directory path, run flake8 in that directory and return the data


def process(path_to_dir):
    python_files = get_python_files(path_to_dir)
    # TODO read .flake8 configuration file and generate the report accoringly
    report = run_flake8(python_files)

    reports = {}
    for key in ['A', 'E', 'F', 'W']:
        rep = report.get_statistics(key)
        for entry in rep:
            # 2 F401 '.controllers' imported but unused
            match = re.search(r'^\d+\s(\w+)\s', entry)
            if not match:
                continue # TODO report
            code = match.group(1)
            if code not in reports:
                reports[code] = 0
            reports[code] += 1
    return reports


# The check_files call prints the report to STDOUT as well.
# So in this function we capture that and discard that output.
def run_flake8(python_files):
    if not python_files:
        return {}
    style_guide = flake8.get_style_guide()
    backup = sys.stdout
    sys.stdout = StringIO()
    report = style_guide.check_files(python_files)
    print("report: {report}")
    #    out = sys.stdout.getvalue()
    sys.stdout = backup
    return report


def get_python_files(path_to_dir):
    if os.path.isfile(path_to_dir):
        return [path_to_dir]
    python_files = []
    for dirname, dirs, files in os.walk(path_to_dir):
        for filename in files:
            if not filename.endswith('.py'):
                continue

            path = os.path.join(dirname, filename)   # relative path to the "current" file
            python_files.append(path)
    return python_files


# '/home/gabor/x/e-commerce'
if __name__ == '__main__':
    # logger = logging.getLogger('PyDigger')
    # logger.setLevel('DEBUG')
    if len(sys.argv) != 2:
        exit(f"Usage: {sys.argv[0]} PATH")
    reports = process(sys.argv[1])
    for code, count in reports.items():
        print(f"{code} {count}")
