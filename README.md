# Easy Zomboid Server (Build 42)

A Project Zomboid template for [AMP](https://cubecoders.com/AMP), the game server control panel by CubeCoders. For Build 42 dedicated servers only.

**Status: built and being tested. Not ready to install yet.**

## The goal

Make running a Project Zomboid server easier, with every setting checked against the game itself.

## Planned

- A plain-English explanation on every setting, grouped by what you're trying to do: joining, PvP, safehouses, zombies, world and time, loot, chat.
- Settings the game no longer reads are grouped at the end, and settings that do nothing on a dedicated server say so.
- The World tab explains how to apply one of the game's presets, or change mods' settings, with the game's own settings editor.
- Warning labels on settings that only apply to a brand new world, or that can reset something.
- A working player count on Build 42.
- Spotting mods that need updating, and restarting with warnings.
- Optional extras you can switch on or off: daily restarts, update night, chat relay, and more.
- Clear guidance on how changes are saved and when they take effect.

## Updating from an earlier version

- Versions before 20 October 2026 never passed the Server save name or the Admin username to the game, so every world was saved as servertest. If you changed Server save name, set it back to servertest before the first start after updating, or the server starts a new world.
- The Admin username now reaches the game, so it must follow the game's name rules in its help text. If it doesn't, the server stops as soon as it starts.
- From 24 October 2026 the server won't start with a Server save name that has anything other than letters, numbers, dashes or underscores, or that starts with a dash. Clicking Update downloads this check even on an instance that keeps an older template version. If your world's name breaks this rule, keep it running as it is and don't click Update.

## Known limits

Things that don't work fully yet, most of them decided by the game or by AMP.

- Updating an instance you already have to a newer template version doesn't work yet: AMP stores this template's source for the instance as "--main". A new instance gets the newest version.
- AMP's player list can keep showing a player whose display name differs from their username, for example after an admin changes it. The game prints the username when a player joins and the display name when they leave.
- Unbanning with unbanuser also sets the account's access level back to user.
- If you press Stop while the server is still starting, AMP waits up to 60 seconds before it stops it.
- The mod list check counts a mod as found even when its mod.info is only in a folder for a newer game version than yours.

## Licence

PolyForm Noncommercial 1.0.0, see [LICENSE.md](LICENSE.md).

You're free to use, copy and change this template for personal and hobby use, and for use by charities, schools and other non-commercial organisations. Commercial use, including offering it as part of paid game server hosting, needs a separate paid licence. To ask, open an issue on this repository or email pippersgaming at gmail dot com.
