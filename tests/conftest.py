import sys, os
ROOT = os.path.dirname(__file__)
PARENT = os.path.abspath(os.path.join(ROOT, '..'))
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)
