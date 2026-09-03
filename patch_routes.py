import re

with open("src/api/routes.py", "r", encoding="utf-8") as f:
    content = f.read()

import_str = "from .auth import Role, require_viewer, require_operator, require_admin, require_auditor\nfrom fastapi import Depends\n"
if "from .auth" not in content:
    content = content.replace("from fastapi import APIRouter", import_str + "from fastapi import APIRouter")

def replacer(match):
    decorator = match.group(1)
    method = match.group(2)
    path = match.group(3)
    async_kw = match.group(4) or ""
    func_name = match.group(5)
    args = match.group(6)
    ret_type = match.group(7) or ""
    
    if "webhooks" in path:
        return match.group(0)
        
    if "Role = Depends" in args:
        return match.group(0)
        
    role = "require_viewer"
    if method.lower() == "post":
        role = "require_operator"
        if "demo" in path or "provider/test-connection" in path:
            role = "require_admin"
    if "audit" in path or "evidence" in path:
        role = "require_auditor"
        
    new_args = f"_role: Role = Depends({role})"
    if args.strip():
        new_args += ", " + args
        
    return f"{decorator}\n{async_kw}def {func_name}({new_args}){ret_type}:"

pattern = re.compile(r'(@router\.(get|post)\("([^"]+)"[^\)]*\))\s+(async\s+)?def\s+([a-zA-Z0-9_]+)\s*\((.*?)\)\s*(->[^:]+)?\s*:', re.DOTALL)
content = pattern.sub(replacer, content)

with open("src/api/routes.py", "w", encoding="utf-8") as f:
    f.write(content)
