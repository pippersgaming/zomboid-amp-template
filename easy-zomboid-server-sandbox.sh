#!/bin/bash
base="$1"
name="$2"
mode="$3"
case "$mode" in
    both|amp|check) ;;
    *) name="" ;;
esac
case "$name" in
    ''|-*|*[!A-Za-z0-9_-]*) echo "[Sandbox] The Server save name can't be used. Use letters, numbers, dashes or underscores only, and don't start it with a dash: Configuration, Server tab, Start here."; exit 1 ;;
esac
[ "$mode" = "check" ] && exit 0
dir="$base/Zomboid/Server"
sandbox="$dir/${name}_SandboxVars.lua"
amp="$dir/${name}_AMPSandbox.lua"
last="$dir/${name}_AMPSandbox.last.lua"
import="$dir/${name}_SandboxImport.ini"
guard="$dir/${name}_AMPSandbox.guard.ini"
[ -f "$base/Zomboid/Saves/Multiplayer/$name/map_sand.bin" ] && echo "[Sandbox] Warning: this world has a map_sand.bin file in its save folder, which single player saves make. The game reads sandbox settings from that file instead of the sandbox file, so AMP's boxes and uploaded settings will not change this world. To switch to the sandbox file: make sure it holds the settings you want, stop the server, and rename map_sand.bin to map_sand.bin.old."
[ -f "$sandbox" ] || exit 0
[ -f "$amp" ] || exit 0

world=0
grep -q '^    ZombieLore = {' "$sandbox" && world=1
stub=0
if [ "$world" = 0 ] && ! tr -d '\r' < "$sandbox" | grep -vE '^[[:space:]]*$|^[[:space:]]*--|^SandboxVars = \{[[:space:]]*$|^[[:space:]]*VERSION = [0-9]+,[[:space:]]*$|^\}[[:space:]]*$|^SandboxVars\.[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)? = ' | grep -q .; then
    stub=1
fi

AWK_LIB='
function clean(v,   n, c) {
    if (v ~ /^".*"$/) { v = substr(v, 2, length(v) - 2); gsub(/\\"/, "\"", v); gsub(/\\\\/, "\\", v) }
    else if (match(v, /^\[=*\[/)) {
        n = RLENGTH; c = "]" substr(v, 2, n - 2) "]"
        if (length(v) >= 2 * n && substr(v, length(v) - n + 1) == c) v = substr(v, n + 1, length(v) - 2 * n)
    }
    return v
}
function norm(v) {
    if (v ~ /^-?[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$/) v = sprintf("%.17g", v + 0)
    return v
}
function setkey(line) { return line ~ /^SandboxVars\.[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)? = / ? substr(line, 1, index(line, " = ") - 1) : "" }
function fixb(line,   h, v, eq) {
    if (line !~ /^SandboxVars\.[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)? = \[==\[.*\]==\][ \t]*$/) return line
    h = substr(line, 1, index(line, " = ") + 2)
    v = substr(line, length(h) + 1); sub(/[ \t]*$/, "", v); v = substr(v, 5, length(v) - 8)
    eq = "=="
    while (index(v, "]" eq "]") || (length(v) > length(eq) && substr(v, length(v) - length(eq)) == "]" eq)) eq = eq "="
    if (eq == "==") return line
    return h "[" eq "[" v "]" eq "]"
}
function value(line) { v = substr(line, index(line, " = ") + 3); sub(/,?[ \t]*$/, "", v); return clean(v) }
function ampkey(line) { k = substr(line, 1, index(line, " = ") - 1); sub(/^SandboxVars\./, "SV_", k); sub(/\./, "_", k); return k }
function isamp(line) { return line ~ /^SandboxVars\.[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)? = / && line !~ / = SandboxVars/ }
'

write_import() {
    known=$(tr -d '\r' < "$amp" | grep -E '^SandboxVars\.[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)? = ' | grep -v ' = SandboxVars' | cut -d' ' -f1 | sed 's/^SandboxVars\./SV_/; s/\./_/')
    tr -d '\r' < "$sandbox" | KNOWN="$known" awk "$AWK_LIB"'
        BEGIN { n = split(ENVIRON["KNOWN"], list, "\n"); for (i = 1; i <= n; i++) ok[list[i]] = 1 }
        function keep(k, v) { if (!(k in ok)) return; if (!(k in seen)) { seen[k] = 1; order[++count] = k } val[k] = v }
        isamp($0) { keep(ampkey($0), value($0)); next }
        /^    [A-Za-z0-9_]+ = \{[ \t]*$/ { t = $1; next }
        /^    \},?[ \t]*$/ { t = ""; next }
        t == "" && /^    [A-Za-z0-9_]+ = .*,[ \t]*$/ { keep("SV_" $1, value($0)); next }
        t != "" && /^        [A-Za-z0-9_]+ = .*,[ \t]*$/ { keep("SV_" t "_" $1, value($0)) }
        END { for (i = 1; i <= count; i++) print order[i] "=" val[order[i]] }
    ' > "$import"
    cp -f "$import" "$guard"
}

if [ "$world" = 1 ] && [ ! -f "$last" ]; then
    cp -f "$amp" "$last"
    write_import
    echo "[Sandbox] Sandbox file from the game found (an existing world or uploaded settings), so its settings were kept and nothing from AMP was applied."
    echo "[Sandbox] To show the world's settings in AMP: in the File Manager, right click Zomboid/Server/${name}_SandboxImport.ini and choose Import Configuration."
    exit 0
fi

if [ "$mode" = "amp" ] || [ ! -f "$last" ]; then
    new=$(tr -d '\r' < "$amp")
else
    new=$(tr -d '\r' < "$amp" | grep -vxF -f <(tr -d '\r' < "$last") | IMPORTED="$guard" awk "$AWK_LIB"'
        BEGIN { f = ENVIRON["IMPORTED"]; while ((getline line < f) > 0) { sub(/\r$/, "", line); i = index(line, "="); if (i > 1) had[substr(line, 1, i) norm(substr(line, i + 1))] = 1 } }
        isamp($0) && ((ampkey($0) "=" norm(value($0))) in had) { next }
        { print }
    ')
fi
if [ "$stub" = 1 ]; then
    new=$(tr -d '\r' < "$amp" | CHOSEN="$new" CURRENT="$sandbox" awk "$AWK_LIB"'
        BEGIN {
            n = split(ENVIRON["CHOSEN"], c, "\n"); for (i = 1; i <= n; i++) chosen[c[i]] = 1
            f = ENVIRON["CURRENT"]; while ((getline line < f) > 0) { sub(/\r$/, "", line); k = setkey(line); if (k != "") isset[k] = 1 }
        }
        ($0 in chosen) || (setkey($0) != "" && !(setkey($0) in isset))
    ')
fi
if [ -n "$new" ]; then
    new=$(printf '%s\n' "$new" | CURRENT="$sandbox" awk "$AWK_LIB"'
        BEGIN { f = ENVIRON["CURRENT"]; while ((getline line < f) > 0) { sub(/\r$/, "", line); sub(/[ \t]+$/, "", line); k = setkey(line); if (k != "") cur[k] = line } }
        { l = fixb($0); t = l; sub(/[ \t]+$/, "", t); k = setkey(t); if (k != "" && (k in cur) && cur[k] == t) next; print l }
    ')
fi
[ -n "$new" ] && printf '\n%s\n' "$new" >> "$sandbox"
[ "$stub" = 1 ] && rm -f "$guard" "$import"
cp -f "$amp" "$last"
[ "$world" = 1 ] && write_import
exit 0
