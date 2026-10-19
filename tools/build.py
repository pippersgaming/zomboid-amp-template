import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "settings.csv"
WORDING_FILE = ROOT / "data" / "wording.csv"
NAME = "easy-zomboid-server"

TABS = {
    "Server": "Server:dns",
    "Players": "Players:group",
    "World": "World:public",
    "Survival": "Survival:backpack",
}

SECTIONS = {
    "Start here": ("Server", "rocket_launch", 1),
    "Joining and access": ("Server", "login", 2),
    "Network and server listing": ("Server", "lan", 3),
    "Mods and map": ("Server", "extension", 4),
    "Saving, backups and resets": ("Server", "save", 5),
    "Performance": ("Server", "speed", 6),
    "Discord and webhooks": ("Server", "forum", 7),
    "Remote admin (RCON)": ("Server", "terminal", 8),
    "Anti-cheat and moderation": ("Server", "gavel", 9),
    "Logging": ("Server", "description", 10),
    "Java and startup": ("Server", "memory", 11),
    "Players and characters": ("Players", "person", 1),
    "Safehouses and factions": ("Players", "home", 2),
    "PvP and safety": ("Players", "shield", 3),
    "Chat and voice": ("Players", "chat", 4),
    "Zombies: population and respawn": ("World", "groups", 1),
    "Zombies: behaviour": ("World", "directions_run", 2),
    "Sandbox control": ("World", "tune", 0),
    "World and time": ("World", "schedule", 3),
    "Weather and nature": ("World", "cloud", 4),
    "Utilities": ("World", "bolt", 5),
    "Map and navigation": ("World", "map", 6),
    "Story and events": ("World", "auto_stories", 7),
    "Loot and items": ("Survival", "inventory_2", 1),
    "Vehicles": ("Survival", "directions_car", 2),
    "Farming, animals and food": ("Survival", "agriculture", 3),
    "Character and skills": ("Survival", "school", 4),
    "Health and combat": ("Survival", "healing", 5),
    "Not used by the game in 42.21": ("Survival", "block", 99),
}

NOT_USED = "Not used by the game in 42.21"

GAME_MANAGED = {"ResetID", "ServerPlayerID"}
STEAM_ID_PATTERN = r"\b7656119\d{10}\b"
NO_EFFECT_ON_SERVER = {"UsePhysicsHitReaction", "DenyLoginOnOverloadedServer", "DisableRadioOverseer",
                       "SandboxVars.FarmingAmountNew", "SandboxVars.SleepingEvent"}
PORT_FIELDS = {"DefaultPort": "$GamePort", "UDPPort": "$DirectPort", "RCONPort": "$RCONPort"}
SECRET_KEYS = {"Password", "RCONPassword", "DiscordToken"}
REQUIRED_INI = {"Map"}
NON_LITERAL_DEFAULT = re.compile(r"random|made by the server", re.I)


def section(name):
    tab, icon, order = SECTIONS[name]
    return TABS[tab], f"{name}:{icon}:{order}"


def readable(key):
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", key).replace("_", " ")
    return words[0].upper() + words[1:]


def load_wording():
    if not WORDING_FILE.exists():
        return {}
    with WORDING_FILE.open(encoding="utf-8") as f:
        return {w["path"]: w for w in csv.DictReader(f)}


WORDING = load_wording()


def plain_label(r):
    if r["table_path"] in WORDING:
        return WORDING[r["table_path"]]["label"]
    label = r["game_label"]
    if not label or "(the Host screen shows the key name)" in label:
        label = readable(r["table_path"].split(".")[-1])
    return label


def display_name(r):
    label = plain_label(r)
    if r["table_path"].startswith("SandboxVars.ZombieLore.") and "zombie" not in label.lower():
        label = "Zombie " + label[0].lower() + label[1:]
    tags = []
    if "New world only" in r["danger_labels"]:
        tags.append("new world only")
    if "Can wipe or reset" in r["danger_labels"]:
        tags.append("can wipe or reset")
    if r["table_path"].startswith("SandboxVars.MultiplierConfig.") and "multiplier" not in label.lower():
        label += " XP multiplier"
    if tags and label.endswith(")"):
        label = label[:-1] + ", " + ", ".join(tags) + ")"
    elif tags:
        label += " (" + ", ".join(tags) + ")"
    return label


def description(r):
    wording = WORDING.get(r["table_path"])
    explanation = wording["help"].strip() if wording else r["plain_explanation"].strip()
    said = explanation.lower()
    parts = [explanation]
    danger = r["danger_labels"]
    if "Unvisited areas only" in danger and "visited" not in said and "explored" not in said:
        parts.append("This only affects places nobody has visited yet. Explored areas keep what they had.")
    if "New world only" in danger and "new world" not in said:
        parts.append("Only used when a new world is created. Changing this later does nothing.")
    if "Can wipe or reset" in danger:
        parts.append("Careful: changing this can make players lose their local data or start it again.")
    if "No effect in 42.21" in danger and "no code" not in said:
        parts.append("The game (version 42.21) doesn't use this setting, so changing it does nothing.")
    if r["recommended_for"] and not wording:
        parts.append(r["recommended_for"].strip())
    parts.append(f"In the settings file: {r['table_path'].replace('SandboxVars.', '')}.")
    return " ".join(p for p in parts if p)


def number(text):
    text = text.split(" ")[0]
    value = float(text)
    return int(value) if value.is_integer() else value


def parse_choices(text):
    run = re.fullmatch(r"(\d+)=(\d+)( \w+)?, \d+=\d+(?: \w+)?, and so on up to (\d+)=\d+(?: \w+)?", text.strip())
    if run:
        first, start, unit, last = int(run.group(1)), int(run.group(2)), (run.group(3) or "").strip(), int(run.group(4))
        out = {}
        for value in range(first, last + 1):
            n = start + value - first
            word = unit[:-1] if unit.endswith("s") and n == 1 else unit
            out[str(value)] = f"{n} {word}".strip()
        return out
    out = {}
    for part in text.split("; "):
        value, label = part.split("=", 1)
        out[value.strip()] = label.strip()[0].upper() + label.strip()[1:]
    return out


def default_value(r):
    d = r["default"]
    if NON_LITERAL_DEFAULT.search(d):
        return ""
    return d


def base_field(r, field_name, param, tab, sub):
    return {
        "DisplayName": display_name(r),
        "Category": tab,
        "Subcategory": sub,
        "Description": description(r),
        "Keywords": ",".join(dict.fromkeys(
            [r["key"].split(".")[-1].lower()] + re.findall(r"[a-z]{3,}", plain_label(r).lower()))),
        "FieldName": field_name,
        "ParamFieldName": param,
        "IncludeInCommandLine": False,
    }


def typed(field, r, is_sandbox):
    t = r["type"]
    d = default_value(r)
    if t == "boolean":
        field["InputType"] = "checkbox"
        field["EnumValues"] = {"False": "false", "True": "true"}
        field["DefaultValue"] = d.lower()
    elif t == "choice" and "=" in r["choices"]:
        field["InputType"] = "enum"
        field["EnumValues"] = parse_choices(r["choices"])
        field["DefaultValue"] = d
    elif t in ("integer", "decimal", "choice"):
        field["InputType"] = "number"
        if r["min"]:
            field["MinValue"] = number(r["min"])
        if r["max"] and "no real limit" not in r["max"]:
            field["MaxValue"] = number(r["max"])
        field["DefaultValue"] = d
    elif t == "text":
        field["InputType"] = "Textarea"
        field["DefaultValue"] = d
    else:
        field["InputType"] = "Password" if r["key"] in SECRET_KEYS else "text"
        field["DefaultValue"] = d
    if is_sandbox and field["InputType"] in ("number", "enum"):
        field["Required"] = True
    return field


def setting_fields(rows):
    fields, lua_lines = [], []
    for r in rows:
        key = r["key"]
        is_sandbox = r["file"] == "SandboxVars"
        group = NOT_USED if "No effect in 42.21" in r["danger_labels"] or r["table_path"] in NO_EFFECT_ON_SERVER else r["group"]
        tab, sub = section(group)
        if not is_sandbox and key in GAME_MANAGED:
            continue
        if not is_sandbox and key in PORT_FIELDS:
            fields.append({
                "DisplayName": key, "Category": tab, "Subcategory": sub,
                "Description": "Set from the ports AMP gives this instance.",
                "FieldName": PORT_FIELDS[key], "ParamFieldName": key,
                "InputType": "hidden", "IncludeInCommandLine": False, "DefaultValue": r["default"],
            })
            continue
        if not is_sandbox and key == "MaxPlayers":
            f = typed(base_field(r, "$MaxUsers", "MaxPlayers", tab, sub), r, False)
            fields.append(f)
            continue
        if is_sandbox:
            path = r["table_path"].replace("SandboxVars.", "")
            field_name = "SV_" + path.replace(".", "_")
            f = typed(base_field(r, field_name, field_name, tab, sub), r, True)
            if f["InputType"] == "text":
                lua_lines.append(f"SandboxVars.{path} = [==[{{{{{field_name}}}}}]==]")
            else:
                lua_lines.append(f"SandboxVars.{path} = {{{{{field_name}}}}}")
        else:
            f = typed(base_field(r, key, key, tab, sub), r, False)
            if key in REQUIRED_INI:
                f["Required"] = True
        fields.append(f)
    return fields, lua_lines


def ini_starter(rows):
    lines = []
    for r in rows:
        if r["file"] != "ini" or r["key"] in GAME_MANAGED:
            continue
        lines.append(f"{r['key']}={default_value(r)}")
    return "\n".join(lines) + "\n"


def template_fields():
    tab, start = section("Start here")
    _, java = section("Java and startup")
    _, rcon = section("Remote admin (RCON)")
    _, mods = section("Mods and map")
    world, sandbox = section("Sandbox control")
    return [
        {
            "DisplayName": "Show players in AMP",
            "Category": tab, "Subcategory": start, "Order": 6,
            "Description": (
                "On: AMP shows who's online, and its kick and ban buttons and 'last player leaves' tasks work. "
                "Build 42 no longer prints joins and leaves to the console, so without this AMP always shows 0 players. "
                "This starts the server with the game's detailed log, which also prints player IP addresses and RCON passwords. "
                "AMP's console hides both, but the game's own server-console.txt file still has them, so only give file access to people you trust. "
                "The detailed log adds some extra lines to the console too."
            ),
            "Keywords": "players,online,count,tracking,join,leave,debuglog",
            "FieldName": "PlayerTracking", "ParamFieldName": "PlayerTracking",
            "InputType": "checkbox", "IncludeInCommandLine": False, "DefaultValue": "-debuglog=DetailedInfo",
            "EnumValues": {"False": "", "True": "-debuglog=DetailedInfo"},
        },
        {
            "DisplayName": "Hide Steam IDs in AMP's console",
            "Category": tab, "Subcategory": start, "Order": 7,
            "Description": (
                "On: players' Steam account numbers show as [hidden] in AMP's console, like their IP addresses. "
                "The game's own log files still have them. Turn this off if you need to see which Steam account a player used."
            ),
            "Keywords": "steam,id,steamid,privacy,hide,console",
            "FieldName": "HideSteamIDs", "ParamFieldName": "HideSteamIDs",
            "InputType": "checkbox", "IncludeInCommandLine": False, "DefaultValue": STEAM_ID_PATTERN,
            "EnumValues": {"False": "(?!)", "True": STEAM_ID_PATTERN},
        },
        {
            "DisplayName": "Mod update warning",
            "Category": tab, "Subcategory": mods, "Order": 4,
            "Description": (
                "The message everyone in game sees when the server finds a Workshop mod update. "
                "The server only checks when it's told to: in AMP, open Schedule and add a task that sends the console command "
                "checkModsNeedUpdate every 10 or 15 minutes. Players who already have the new version can't join until the server restarts, "
                "so restart when it suits you. Leave this empty to send no message."
            ),
            "Keywords": "mod,update,workshop,warning,restart,checkmodsneedupdate",
            "FieldName": "ModUpdateMessage", "ParamFieldName": "ModUpdateMessage",
            "InputType": "text", "IncludeInCommandLine": False,
            "DefaultValue": "A mod has been updated. The server will restart soon to install it.",
        },
        {
            "DisplayName": "Admin password",
            "Category": tab, "Subcategory": start, "Order": 1,
            "Description": (
                "Required. The password for your in-game admin account (the username below), not the one players use to join. "
                "The game resets the admin account to this password every time the server starts. "
                "Use a password you don't use anywhere else: anyone you give access to this server in AMP may be able to see it. "
                "Every box on these pages saves when you click away from it and takes effect after a restart. "
                "Change server settings in these boxes, not in the game's .ini file, because AMP rewrites that file from them every time the server starts."
            ),
            "Keywords": "admin,password,adminpassword,start,first",
            "FieldName": "adminpassword", "ParamFieldName": "adminpassword",
            "InputType": "Password", "Required": True,
            "IncludeInCommandLine": True, "SkipIfEmpty": True, "DefaultValue": "",
        },
        {
            "DisplayName": "Admin username",
            "Category": tab, "Subcategory": start, "Order": 3,
            "Description": (
                "The name of your in-game admin account. The game creates it on the first start. "
                "If your game is started in debug mode, only admin accounts can join: others see 'Debug connection is not allowed for non admin.'"
            ),
            "Keywords": "admin,username,adminusername",
            "FieldName": "adminusername", "ParamFieldName": "adminusername",
            "InputType": "text", "Required": True,
            "IncludeInCommandLine": True, "SkipIfEmpty": True, "DefaultValue": "admin",
        },
        {
            "DisplayName": "Server save name (careful)",
            "Category": tab, "Subcategory": start, "Order": 4,
            "Description": (
                "The name the game uses for this server's settings files and world. "
                "Changing this starts a brand new world with fresh settings files. The old world stays on disk under its old name. "
                "Use letters, numbers, dashes or underscores only."
            ),
            "Keywords": "server,name,servername,world,save",
            "FieldName": "servername", "ParamFieldName": "servername",
            "InputType": "text", "Required": True,
            "IncludeInCommandLine": True, "SkipIfEmpty": True, "DefaultValue": "servertest",
        },
        {
            "DisplayName": "Memory limit",
            "Category": tab, "Subcategory": start, "Order": 5,
            "Description": (
                "The most memory (RAM) the server can use. It starts at 3072 MB (3 GB). "
                "The game's own dedicated server files give two figures: 3 GB in ProjectZomboid64.json, and 16 GB in StartServer64.bat on Windows. "
                "For Build 42 we recommend at least 10240 MB (10 GB), adjusted for the mods you run. "
                "The game's memory manager grows towards this limit whether it needs the memory or not, so leave enough for Windows "
                "and anything else running on the machine. If the console shows OutOfMemoryError, raise this."
            ),
            "Keywords": "memory,ram,xmx,limit,heap",
            "FieldName": "MaxMemory", "ParamFieldName": "MaxMemory",
            "InputType": "number", "MinValue": 2048, "MaxValue": 65536, "Suffix": "MB",
            "Required": True, "IncludeInCommandLine": False, "DefaultValue": "3072",
        },
        {
            "DisplayName": "Sandbox changes made in game",
            "Category": world, "Subcategory": sandbox, "Order": 1,
            "Description": (
                "Decides who wins when a sandbox setting (zombies, loot, world and so on) is changed both here and in the game's admin menu. "
                "Last change wins: when the server starts, only the boxes you've changed here since the last start are applied, so changes made in game are kept. "
                "AMP always wins: every sandbox box is applied each time the server starts, so changes made in game only last until a restart. "
                "Mod sandbox settings are never touched, whichever you pick. "
                "To make these boxes match what the game is really using, after changes in game or after bringing in a world: start the server once, "
                "then in the File Manager right click Zomboid/Server/servertest_SandboxImport.ini (your save name in place of servertest) and choose Import Configuration. "
                "A world you bring in is safe: on its first start here, nothing from AMP is applied to it until you import or change a box. "
                "Presets and mod settings: use the game's own settings editor. On your PC, open Project Zomboid, click HOST, then Manage settings, "
                "then Create New Settings or Edit Selected Settings. Give it the same name as this server's save name. "
                "Choose the same mods as this server, use Apply Preset if you want one, change anything you like, and save. "
                "It's saved in the Zomboid\\Server folder in your user folder. Stop this server, upload only the saved servertest_SandboxVars.lua "
                "to Zomboid/Server in the File Manager, replacing the old one, then start and import as above. "
                "Leave the .ini it also saves, because AMP's own boxes set those settings. "
                "With AMP always wins, AMP's boxes replace the uploaded sandbox settings."
            ),
            "Keywords": "sandbox,in game,admin menu,sync,control,overwrite",
            "FieldName": "SandboxControl", "ParamFieldName": "SandboxControl",
            "InputType": "enum", "IncludeInCommandLine": False, "DefaultValue": "both",
            "EnumValues": {"both": "Last change wins (AMP or game)", "amp": "AMP always wins"},
        },
        {
            "DisplayName": "Memory manager (Java garbage collector)",
            "Category": tab, "Subcategory": java, "Order": 1,
            "Description": "ZGC is what the game's own launcher uses on Windows 10 and later, and G1GC is what it uses on older Windows. ZGC grows towards the memory limit even when it doesn't need the memory.",
            "Keywords": "java,gc,zgc,g1gc,garbage,collector",
            "FieldName": "JavaGC", "ParamFieldName": "JavaGC",
            "InputType": "enum", "IncludeInCommandLine": False, "DefaultValue": "-XX:+UseZGC",
            "EnumValues": {"-XX:+UseZGC": "ZGC (game default)", "-XX:+UseG1GC": "G1GC"},
        },
        {
            "DisplayName": "Extra Java options",
            "Category": tab, "Subcategory": java, "Order": 2,
            "Description": "Added to the Java part of the start command. Leave this empty unless a guide tells you what to add.",
            "Keywords": "java,arguments,options,jvm",
            "FieldName": "CustomJavaArgs", "ParamFieldName": "CustomJavaArgs",
            "InputType": "text", "IncludeInCommandLine": False, "DefaultValue": "",
        },
        {
            "DisplayName": "Extra server options",
            "Category": tab, "Subcategory": java, "Order": 3,
            "Description": "Added to the end of the start command, for example -ip 192.168.1.10 to use one network address. Leave this empty unless you need it.",
            "Keywords": "server,arguments,options,ip",
            "FieldName": "CustomServerArgs", "ParamFieldName": "CustomServerArgs",
            "InputType": "text", "IncludeInCommandLine": False, "DefaultValue": "",
        },
        {
            "DisplayName": "RCON from this machine only",
            "Category": tab, "Subcategory": rcon, "Order": 1,
            "Description": (
                "RCON lets other programs, like a Discord bot or an admin tool, send commands to the server using the RCON password (set in Start here). "
                "When this is on, only programs on this server machine can use RCON, so nothing on your network or the internet can reach it. "
                "Turn it off only if a program on another machine needs RCON, and keep the RCON port closed on your router."
            ),
            "Keywords": "rcon,local,loopback,security",
            "FieldName": "RconLocalOnly", "ParamFieldName": "RconLocalOnly",
            "InputType": "checkbox", "IncludeInCommandLine": False, "DefaultValue": "-Drconlo=true",
            "EnumValues": {"False": "", "True": "-Drconlo=true"},
        },
        {
            "DisplayName": "Game version",
            "Category": "Updates", "Subcategory": "Project Zomboid:download:1", "Order": 1,
            "Description": (
                "Build 42 is the game's normal Steam version. Unstable gets test builds first, and players must be on the same version as the server to join. "
                "After changing this, stop the server, click Update, then start it. Build 41 worlds don't load in Build 42. "
                "Don't put mods in AMP's own Steam Workshop box on this page, because it causes a Steam login loop. "
                "Add mods in Configuration, Server, Mods and map."
            ),
            "Keywords": "branch,beta,unstable,version,build,update,workshop",
            "FieldName": "GameBranch", "ParamFieldName": "GameBranch",
            "InputType": "enum", "IncludeInCommandLine": False, "DefaultValue": "public",
            "EnumValues": {"public": "Build 42 (normal)", "unstable": "Build 42 unstable (test builds)"},
        },
    ]


def start_here_overrides(fields):
    tab, start = section("Start here")
    for f in fields:
        if f.get("ParamFieldName") == "RCONPassword":
            f.update({
                "DisplayName": "RCON password",
                "Category": tab, "Subcategory": start, "Order": 2, "Required": True,
                "Description": (
                    "Required. RCON lets other programs, like a Discord bot or an admin tool, send commands to the server using this password. "
                    "Use a long password you don't use anywhere else: anyone you give access to this server in AMP may be able to see it, "
                    "and the game keeps it in plain text in its settings file. "
                    "By default only programs on this server machine can use RCON: see 'RCON from this machine only' in Remote admin (RCON)."
                ),
            })


def mods_notes(fields):
    notes = {
        "Mods": (
            "The mod IDs to load, separated by semicolons, for example ModA;ModB. "
            "Each mod also needs its Workshop item number in Workshop Items, or nothing loads. "
            "One Workshop item can hold several mod IDs, so list each one you want. "
            "A backslash before an ID (\\ModA) is optional, because the game removes backslashes before reading this list."
        ),
        "WorkshopItems": (
            "The Steam Workshop item numbers, separated by semicolons with no spaces. "
            "Each number is at the end of the mod's Workshop page address, after id=. The game downloads these itself when the server starts. "
            "Don't use AMP's own Steam Workshop box on the Updates page."
        ),
        "Map": (
            "The map folders to load, separated by semicolons. Map mods go first and Muldraugh, KY goes last, "
            "for example MapModA;Muldraugh, KY. This can't be empty."
        ),
        "WebhookAddress": (
            "A web address the server posts short messages to: players joining and leaving, anti-cheat reports, "
            "and the server opening or closing. It works with a Discord webhook, no bot needed: in Discord, open the channel's settings, "
            "then Integrations, Webhooks, New Webhook, Copy Webhook URL. Paste it here and add /slack to the end."
        ),
    }
    for f in fields:
        if f.get("ParamFieldName") in notes:
            f["Description"] = notes[f["ParamFieldName"]]
            f["Order"] = {"Mods": 1, "WorkshopItems": 2, "Map": 3, "WebhookAddress": 1}[f["ParamFieldName"]]


SANDBOX_STARTER ="SandboxVars = {\n    VERSION = 6,\n}\n"


def starter_stages(rows):
    server_dir = "{{$FullBaseDir}}Zomboid/Server"
    return [
        {
            "UpdateStageName": "Create settings folder",
            "UpdateSourcePlatform": "All",
            "UpdateSource": "CreateDirectory",
            "UpdateSourceArgs": server_dir,
            "SkipOnFailure": False,
        },
        {
            "UpdateStageName": "Create server settings file if missing",
            "UpdateSourcePlatform": "All",
            "UpdateSource": "CreateFile",
            "UpdateSourceArgs": server_dir + "/{{servername}}.ini",
            "UpdateSourceData": ini_starter(rows),
            "OverwriteExistingFiles": False,
            "SkipOnFailure": False,
        },
        {
            "UpdateStageName": "Create sandbox settings file if missing",
            "UpdateSourcePlatform": "All",
            "UpdateSource": "CreateFile",
            "UpdateSourceArgs": server_dir + "/{{servername}}_SandboxVars.lua",
            "UpdateSourceData": SANDBOX_STARTER,
            "OverwriteExistingFiles": False,
            "SkipOnFailure": False,
        },
    ]


def prestart_stages(rows):
    return starter_stages(rows) + [
        {
            "UpdateStageName": "Apply sandbox settings",
            "UpdateSourcePlatform": "Windows",
            "UpdateSource": "Executable",
            "UpdateSourceData": "powershell.exe",
            "UpdateSourceArgs": (
                f"-NoProfile -ExecutionPolicy Bypass -File \"{{{{$FullRootDir}}}}{NAME}-sandbox.ps1\" "
                "\"{{$FullBaseDir}}.\" \"{{servername}}\" \"{{SandboxControl}}\""
            ),
            "SkipOnFailure": False,
        },
        {
            "UpdateStageName": "Apply sandbox settings",
            "UpdateSourcePlatform": "Linux",
            "UpdateSource": "Executable",
            "UpdateSourceData": "/bin/bash",
            "UpdateSourceArgs": (
                f"\"{{{{$FullRootDir}}}}{NAME}-sandbox.sh\" "
                "\"{{$FullBaseDir}}.\" \"{{servername}}\" \"{{SandboxControl}}\""
            ),
            "SkipOnFailure": False,
        },
        {
            "UpdateStageName": "Check mod lists",
            "UpdateSourcePlatform": "Windows",
            "UpdateSource": "Executable",
            "UpdateSourceData": "powershell.exe",
            "UpdateSourceArgs": (
                f"-NoProfile -ExecutionPolicy Bypass -File \"{{{{$FullRootDir}}}}{NAME}-modcheck.ps1\" "
                "\"{{$FullBaseDir}}.\" \"{{servername}}\""
            ),
            "SkipOnFailure": True,
        },
        {
            "UpdateStageName": "Check mod lists",
            "UpdateSourcePlatform": "Linux",
            "UpdateSource": "Executable",
            "UpdateSourceData": "/bin/bash",
            "UpdateSourceArgs": f"\"{{{{$FullRootDir}}}}{NAME}-modcheck.sh\" \"{{{{$FullBaseDir}}}}.\" \"{{{{servername}}}}\"",
            "SkipOnFailure": True,
        },
        {
            "UpdateStageName": "Make Java runnable",
            "UpdateSourcePlatform": "Linux",
            "UpdateSource": "SetExecutableFlag",
            "UpdateSourceArgs": "{{$FullBaseDir}}jre64/bin/java",
            "SkipOnFailure": True,
        },
    ]


def main():
    with DATA.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    fields, lua_lines = setting_fields(rows)
    mods_notes(fields)
    start_here_overrides(fields)
    fields = template_fields() + fields
    tables = sorted({r["table_path"].split(".")[1] for r in rows
                     if r["file"] == "SandboxVars" and r["table_path"].count(".") > 1})
    header = "".join(f"SandboxVars.{t} = SandboxVars.{t} or {{}}\n" for t in tables)
    (ROOT / f"{NAME}config.json").write_text(json.dumps(fields, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / f"{NAME}sandbox.lua").write_text(header + "\n".join(lua_lines) + "\n", encoding="utf-8")
    (ROOT / f"{NAME}start.json").write_text(json.dumps(prestart_stages(rows), indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    updates_path = ROOT / f"{NAME}updates.json"
    starters = starter_stages(rows)
    names = {s["UpdateStageName"] for s in starters}
    updates = [s for s in json.loads(updates_path.read_text(encoding="utf-8")) if s["UpdateStageName"] not in names]
    updates_path.write_text(json.dumps(updates + starters, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(fields)} fields, {len(lua_lines)} sandbox lines")


if __name__ == "__main__":
    main()
