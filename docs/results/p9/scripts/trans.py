"""Print the transitions of a replay root between two times as the agent's get_transitions returns them. usage: trans.py <run> <t_a> <t_b> [set]"""
import sys, json
from p9lib import *
from replay import tools_for
s = sys.argv[4] if len(sys.argv) > 4 else "P9"
out = tools_for(s, sys.argv[1]).get_transitions(float(sys.argv[2]), float(sys.argv[3]))
for t in out["transitions"]:
    print(f"{t['id']} frames={t['frames']} t={t['t']} entered={t['entered_text']!r} submitted={t['submitted']} conf={t['confidence']}\n   action: {t['action']}\n   result: {t['result']}")
