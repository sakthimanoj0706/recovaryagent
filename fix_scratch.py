import glob
import os

for filepath in glob.glob("scratch/test_*api.py") + ["tests/test_decision_replay.py"]:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "os.environ['RECOVERAI_ENV'] = 'development'" not in content:
        content = content.replace("import sys", "import sys\nimport os\nos.environ['RECOVERAI_ENV'] = 'development'\n")
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
