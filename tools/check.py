import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "easy-zomboid-server"
INPUT_TYPES = {"checkbox", "enum", "list", "number", "Password", "Radio", "RandomPassword",
               "range", "text", "Textarea", "URL", "UserPassword", "hidden"}
BANNED = re.compile("[–—‘’“”]")
problems = []


def problem(text):
    problems.append(text)


for path in sorted(ROOT.glob("*.json")):
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        problem(f"{path.name}: not valid JSON ({e})")

fields = json.loads((ROOT / f"{NAME}config.json").read_text(encoding="utf-8"))
seen = set()
for f in fields:
    name = f["FieldName"]
    where = f"{name} ({f['DisplayName']})"
    if name in seen:
        problem(f"{where}: FieldName used twice")
    seen.add(name)
    if f["InputType"] not in INPUT_TYPES:
        problem(f"{where}: InputType {f['InputType']} not a known spelling")
    if f.get("Required") and f["InputType"] == "hidden":
        problem(f"{where}: Required and hidden, AMP could never start")
    for key in ("MinValue", "MaxValue", "Order"):
        if key in f and not isinstance(f[key], (int, float)):
            problem(f"{where}: {key} is not a JSON number")
    if "MinValue" in f and "MaxValue" in f and f["MinValue"] > f["MaxValue"]:
        problem(f"{where}: MinValue above MaxValue")
    d = f.get("DefaultValue", "")
    if f["InputType"] in ("checkbox", "enum"):
        values = f["EnumValues"].values() if f["InputType"] == "checkbox" else f["EnumValues"].keys()
        if not f.get("EnumValues"):
            problem(f"{where}: no EnumValues")
        elif d not in values:
            problem(f"{where}: default {d!r} is not one of its options")
    if f["InputType"] == "number" and d != "":
        try:
            n = float(d)
            if "MinValue" in f and n < f["MinValue"] or "MaxValue" in f and n > f["MaxValue"]:
                problem(f"{where}: default {d} outside its range")
        except ValueError:
            problem(f"{where}: number default {d!r} is not a number")
    if f.get("Required") and d == "" and name not in ("adminpassword", "RCONPassword"):
        problem(f"{where}: Required but empty by default")
    for key in ("DisplayName", "Description"):
        if BANNED.search(f.get(key, "")):
            problem(f"{where}: dash or curly quote in {key}")

lua = (ROOT / f"{NAME}sandbox.lua").read_text(encoding="utf-8")
placeholders = set(re.findall(r"\{\{(\w+)\}\}", lua))
sandbox_fields = {f["FieldName"] for f in fields if f["FieldName"].startswith("SV_")}
for missing in sorted(sandbox_fields - placeholders):
    problem(f"sandbox field {missing} has no line in the sandbox template")
for missing in sorted(placeholders - seen):
    problem(f"sandbox template uses {{{{{missing}}}}} but no field has that name")
for line in lua.splitlines():
    if line.startswith("--") or not line.strip():
        continue
    if not re.fullmatch(r"SandboxVars(\.\w+)+ = (\{\{\w+\}\}|\[==\[\{\{\w+\}\}\]==\]|SandboxVars\.\w+ or \{\})", line):
        problem(f"sandbox template line looks wrong: {line}")

for path in sorted(ROOT.iterdir()):
    if path.is_file() and path.suffix in (".json", ".kvp", ".lua", ".ps1", ".sh"):
        text = path.read_text(encoding="utf-8")
        if any(ord(c) < 32 and c not in "\n\r\t" for c in text):
            problem(f"{path.name}: hidden control character")
        if path.suffix == ".sh" and "\r" in text:
            problem(f"{path.name}: Windows line endings in a Linux script")

AMP_VALUES = {"username", "userid"}
kvp = (ROOT / f"{NAME}.kvp").read_text(encoding="utf-8")
used = set(re.findall(r"\{\{(\w+)\}\}", kvp))
for name in sorted(used - seen - AMP_VALUES):
    problem(f"kvp uses {{{{{name}}}}} but no setting has that FieldName")
for retired in ("App.MonitorChildProcess=", "App.MonitorChildProcessWaitMs", "Console.ActivateLogRegex",
                "App.SteamWorkshopDownloadLocation", "App.RCONConnectRetrySeconds", "App.SteamForceLoginPrompt"):
    if retired in kvp:
        problem(f"kvp still has retired key {retired}")

if problems:
    print(f"{len(problems)} problem(s):")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print(f"All checks passed: {len(fields)} settings, {len(placeholders)} sandbox lines.")
