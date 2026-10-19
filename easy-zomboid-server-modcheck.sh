#!/bin/bash
base="$1"
name="$2"
ini="$base/Zomboid/Server/$name.ini"
[ -f "$ini" ] || exit 0

split_list() {
    tr -d '\\\r' | tr ';' '\n' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' | grep -v '^$'
}

mods=$(grep '^Mods=' "$ini" | tail -n 1 | cut -d= -f2- | split_list)
items=$(grep '^WorkshopItems=' "$ini" | tail -n 1 | cut -d= -f2- | split_list)
content="$base/steamapps/workshop/content/108600"
all_ids=$(mktemp)
warnings=$(mktemp)
not_downloaded=""

while IFS= read -r item; do
    [ -z "$item" ] && continue
    dir="$content/$item"
    if [ ! -d "$dir" ]; then
        not_downloaded="${not_downloaded:+$not_downloaded, }$item"
        continue
    fi
    ids=$(for f in "$dir"/mods/*/common/mod.info "$dir"/mods/*/42/mod.info "$dir"/mods/*/42.*/mod.info; do [ -f "$f" ] && grep -h '^id=' "$f"; done | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' | grep -v '^$' | sort -u)
    printf '%s\n' "$ids" >> "$all_ids"
    if [ -n "$ids" ] && ! printf '%s\n' "$ids" | grep -qxF -f <(printf '%s\n' "$mods"); then
        echo "Workshop item $item is listed, but none of its mods are in Mods. Its mod IDs: $(printf '%s' "$ids" | paste -sd, - | sed 's/,/, /g')." >> "$warnings"
    fi
done <<< "$items"

while IFS= read -r m; do
    [ -z "$m" ] && continue
    if ! grep -qxF -- "$m" "$all_ids"; then
        if [ -n "$not_downloaded" ]; then
            echo "Mod ID '$m' was not found in the downloaded Workshop items. It may be in one not downloaded yet." >> "$warnings"
        else
            echo "Mod ID '$m' is not in any listed Workshop item. Check its Workshop number is in Workshop items and the ID is spelled exactly as on its Workshop page." >> "$warnings"
        fi
    fi
done <<< "$mods"

mod_count=$(printf '%s' "$mods" | grep -c . )
item_count=$(printf '%s' "$items" | grep -c . )
echo "[Mod check] $mod_count mod IDs and $item_count Workshop items listed."
[ -n "$not_downloaded" ] && echo "[Mod check] Not downloaded yet, normal before the first start with them: $not_downloaded."
if [ -s "$warnings" ]; then
    sed 's/^/[Mod check] /' "$warnings"
else
    echo "[Mod check] Mods and Workshop items match."
fi
rm -f "$all_ids" "$warnings"
exit 0
