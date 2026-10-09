#!/bin/bash
base="$1"
name="$2"
mode="$3"
dir="$base/Zomboid/Server"
sandbox="$dir/${name}_SandboxVars.lua"
amp="$dir/${name}_AMPSandbox.lua"
last="$dir/${name}_AMPSandbox.last.lua"
import="$dir/${name}_SandboxImport.ini"
[ -f "$base/Zomboid/Saves/Multiplayer/$name/map_sand.bin" ] && echo "[Sandbox] Warning: this world has a map_sand.bin file in its save folder, which single player saves make. The game reads sandbox settings from that file instead of the sandbox file, so AMP's boxes and uploaded settings will not change this world. To switch to the sandbox file: make sure it holds the settings you want, stop the server, and rename map_sand.bin to map_sand.bin.old."
[ -f "$sandbox" ] || exit 0

world=0
grep -q '^    ZombieLore = {' "$sandbox" && world=1

if [ "$world" = 1 ] && [ -f "$amp" ]; then
    known=$(tr -d '\r' < "$amp" | grep -E '^SandboxVars\.[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)? = ' | grep -v ' = SandboxVars' | cut -d' ' -f1 | sed 's/^SandboxVars\./SV_/; s/\./_/')
    tr -d '\r' < "$sandbox" | awk -v known="$known" '
        BEGIN { n = split(known, list, "\n"); for (i = 1; i <= n; i++) ok[list[i]] = 1 }
        function clean(v) {
            if (v ~ /^".*"$/) { v = substr(v, 2, length(v) - 2); gsub(/\\"/, "\"", v); gsub(/\\\\/, "\\", v) }
            return v
        }
        function value(line) { v = substr(line, index(line, " = ") + 3); sub(/,[ \t]*$/, "", v); return clean(v) }
        /^    [A-Za-z0-9_]+ = \{[ \t]*$/ { t = $1; next }
        /^    \},?[ \t]*$/ { t = ""; next }
        t == "" && /^    [A-Za-z0-9_]+ = .*,[ \t]*$/ { k = "SV_" $1; if (k in ok) print k "=" value($0); next }
        t != "" && /^        [A-Za-z0-9_]+ = .*,[ \t]*$/ { k = "SV_" t "_" $1; if (k in ok) print k "=" value($0) }
    ' > "$import"
fi

[ -f "$amp" ] || exit 0

if [ "$world" = 1 ] && [ ! -f "$last" ]; then
    cp -f "$amp" "$last"
    echo "[Sandbox] Sandbox file from the game found (an existing world or uploaded settings), so its settings were kept and nothing from AMP was applied."
    echo "[Sandbox] To show the world's settings in AMP: in the File Manager, right click Zomboid/Server/${name}_SandboxImport.ini and choose Import."
    exit 0
fi

echo >> "$sandbox"
if [ "$mode" = "amp" ] || [ ! -f "$last" ]; then
    cat "$amp" >> "$sandbox"
else
    grep -vxF -f "$last" "$amp" >> "$sandbox"
fi
cp -f "$amp" "$last"
exit 0
