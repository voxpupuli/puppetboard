#!/usr/bin/env python

import glob
import re
try:
    import future.utils
except:
    pass


for req_file in glob.glob('requirements*.txt'):
    new_data = []
    with open(req_file, 'r') as fp:
        data = fp.readlines()
        for line in data:
            new_data.append(re.sub(r'==\d+(\.\d+){0,3}\s+$', '\n', line))

    with open(req_file, 'w') as fp:
        fp.writelines(new_data)
