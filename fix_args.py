import re
with open("src/api/routes.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove the previously injected roles
content = re.sub(r'(_role:\s*Role\s*=\s*Depends\([^\)]+\)),\s*', '', content)
content = re.sub(r',?\s*(_role:\s*Role\s*=\s*Depends\([^\)]+\))', '', content)

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
        
    role = "require_viewer"
    if method.lower() == "post":
        role = "require_operator"
        if "demo" in path or "provider/test-connection" in path:
            role = "require_admin"
    if "audit" in path or "evidence" in path:
        role = "require_auditor"
        
    new_args = args.strip()
    if new_args:
        new_args += f", _role: Role = Depends({role})"
    else:
        new_args = f"_role: Role = Depends({role})"
        
    return f"{decorator}\n{async_kw}def {func_name}({new_args}){ret_type}:"

pattern = re.compile(r'(@router\.(get|post)\("([^"]+)"[^\)]*\))\s+(async\s+)?def\s+([a-zA-Z0-9_]+)\s*\((.*?)\)\s*(->[^:]+)?\s*:', re.DOTALL)
content = pattern.sub(replacer, content)

with open("src/api/routes.py", "w", encoding="utf-8") as f:
    f.write(content)
