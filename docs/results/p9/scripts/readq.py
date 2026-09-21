"""Per question: how many of the four answers of each set say anything about readers, sightings or stability."""
import re
from p9lib import *
READ = re.compile(r"readers? (dis)?agree|readers? differ|two readers|both readers|one reader|single reader|only one reader|ocr (only|read|reads|reading|rendered|renders|sometimes|occasionally|misread|captured|gave|pass)|read by ocr|vision (reader|model)|vlm|model reads|seen once|single (captured )?frame|one sighting|1 sighting|sightings|unstable|other ocr reading|ocr[- ]derived|ocr and", re.I)
print("Q    P4 P9 P8   (answers of 4 that mention readers, sightings or stability)")
for q in QIDS:
    print(f"{q:4} " + "  ".join(str(sum(1 for r in RUNS if READ.search(answers(s, r)[q]["answer"]))) for s in ("P4", "P9", "P8")))
print("all  " + "  ".join(str(sum(1 for q in QIDS for r in RUNS if READ.search(answers(s, r)[q]["answer"]))) for s in ("P4", "P9", "P8")))
