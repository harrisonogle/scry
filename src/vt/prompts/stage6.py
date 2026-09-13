VERSION = "s6-v1"

BOUNDARY_SYSTEM = """You segment an ordered list of items from a computer tutorial into coherent units.

Each line is one item: its id, its frame range and time range, and a one-line summary. Output only the ids at which a new segment begins, with a short label for the segment that starts there. A segment is a coherent unit of work a tutorial reader would follow as one step (for steps) or one topic (for sections). The first item always begins the first segment. Use ids exactly as listed; do not invent ids.

Worked example for the boundary call. Given items
T1 [f0→f2, 0.0–3.1s] Browser: Portal: 3 text changes
T2 [f2→f5, 3.1–9.8s] Browser: Portal: typed "RG1-KodeKloud-AKS"
T3 [f5→f9, 9.8–20.2s] Browser: Portal: 12 text changes — clicked Review + create
T4 [f9→f12, 20.2–31.0s] Windows Terminal: typed "az aks get-credentials --resource-group RG1-KodeKloud-AKS --name AKS1"
T5 [f12→f14, 31.0–40.5s] Windows Terminal: 6 lines appended
a good answer is {"segments": [{"start_id": "T1", "label": "Create the resource group in the portal"}, {"start_id": "T4", "label": "Connect to the cluster from the terminal"}]}: the first item starts the first segment, and the new segment begins where the sub-goal changes (portal work → terminal work), not at every item."""

ELABORATE_SYSTEM = """You describe one segment of a computer tutorial for a reader who will follow it.

You are given the segment's items in full and the screen state at its start and end. Return a short label and a description. Every sentence of the description must carry, in square brackets, the ids of the items it rests on, e.g. [T13]. Quote commands, paths and identifiers exactly as given; do not paraphrase or correct them. List every cited id in refs.

Worked example. For a segment whose items are T4 (typed "az aks get-credentials --resource-group RG1-KodeKloud-AKS --name AKS1") and T5 (6 lines appended: "Merged \"AKS1\" as current context in C:\\Users\\msadmin\\.kube\\config"), a good answer is {"label": "Connect kubectl to the cluster", "description": "Run `az aks get-credentials --resource-group RG1-KodeKloud-AKS --name AKS1` in the terminal [T4]. The command merges the cluster's credentials into the local kubeconfig and reports \"Merged \\\"AKS1\\\" as current context\" [T5].", "refs": ["T4", "T5"]}. A poor answer paraphrases the command (dropping the resource-group flag) or leaves a sentence without a bracketed id."""
