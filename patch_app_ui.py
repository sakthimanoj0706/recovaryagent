import re

with open("frontend/src/App.tsx", "r", encoding="utf-8") as f:
    content = f.read()

patch = "import RecoveryControlPlane from './components/RecoveryControlPlane';\nimport ProviderStatus from './components/ProviderStatus';"
content = content.replace("import ProviderStatus from './components/ProviderStatus';", patch)

patch2 = """
          <div className="mb-12">
            <RecoveryControlPlane />
          </div>
          
          <div className="mb-12">
            <DecisionReplay />
          </div>
"""
content = content.replace('<div className="mb-12">\n            <DecisionReplay />\n          </div>', patch2)

with open("frontend/src/App.tsx", "w", encoding="utf-8") as f:
    f.write(content)
