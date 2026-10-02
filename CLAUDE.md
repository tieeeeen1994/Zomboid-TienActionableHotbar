# Tien's Actionable Hotbar

Project Zomboid B42 mod (client only): each hotbar slot can do any action from its item's own context menu instead of
the vanilla equip / toggle (right-click the item > Change Default Action). The live code is under
`Contents/mods/TienActionableHotbar/42/`. General engine findings (ISHotbar, context menu internals) go in
`~/Zomboid/Workshop/ZomboidFixesB42/CLAUDE.md` ("UI building blocks learned for the hotbar"); this file only holds the
reasoning behind this mod.

The Lua source has no comments on purpose. Non-obvious reasoning lives here; update this file when it changes.

## Status

First implementation (2026-10-02), not yet run in game. Only checked with luaparser (syntax and free globals). See
"To verify".

## How vanilla (and PAR) decide what a slot does

- Clicking a slot (`ISHotbar:onMouseUp`) and its number key (`ISHotbar.onKeyPressed`, skipped while the action queue
  is not empty, while attacking, paused, or with a joypad) both end in `ISHotbar:activateSlot(slotIndex)`
  (`client/Hotbar/ISHotbar.lua:548`, 42.20): items that `canBeActivated` and are not HandWeapons toggle, everything else
  goes to `equipItem` (`:575`), which unequips if held, else `ISEquipWeaponAction(both_hands = isTwoHandWeapon(),
  primary = both_hands or IsWeapon())`. That is why a bat always takes both hands and a bottle goes to the off hand.
- Right-clicking a filled slot (`ISHotbar:doMenu` `:82`) opens `ISInventoryPaneContextMenu.createMenu(playerNum, true,
  {item}, x, y)` (the item's full inventory menu), then adds Attach for other items.
- Plysken Attachments Reborn (workshop 3749848348, `client/Hotbar/PAR_ISHotbar.lua:151`) **replaces** `activateSlot`
  at file load: clothing is worn / taken off, activatable non-weapons toggle, HandWeapon / InventoryContainer / Radio
  are equipped, anything else (its bottles, pills, toys) does nothing. PAR makes ~110 more items attachable
  (`shared/PAR_ItemTweaks.lua`: Bottle, Wine, PillBottle, Container..., via `DoParam("AttachmentType = ...")`).

## Files

- `client/TienActionableHotbar_Core.lua`: records, storage, menu snapshot and matching.
  - A **record** = `{ path = { option names root → leaf }, fn = "Table.key" | nil, params = { [i] = "n:1" | "s:..." |
    "b:true" } }`. `fn` is the option's `onSelect` found by identity (`FunctionName`: first in
    ISInventoryPaneContextMenu, ISHotbar, ISWorldObjectContextMenu, ISTimedActionQueue, then one level of every global
    table, cached; nil for anonymous local functions). `params` = the scalar `param1..10` only (items lists, players are
    not kept).
  - `Match(leaves, rec)`: exact path (and same function if it resolves) first; else, among leaves with the same
    `onSelect`: same scalars and same leaf name, then same scalars, then same leaf name, then the only one. This keeps a
    choice working when the menu wording changes with the item's state ("Open and Drink" vs "Drink", both
    `onDrinkFluid` with param1 = 1 / 0.5 / 0.25) or with the game language.
  - **Every <type>** records: `Zomboid/Lua/TienActionableHotbar.ini` (one file per computer): `version=1`, then per
    type `item=<fullType>`, `fn=`, `param=<i>:<code>`, `path=<name>` (one line per level). Saved on every change.
  - **Only this <item>** records: player modData `TienActionableHotbar[<item ID>]`, `transmitModData()` in MP (what the
    vanilla hotbar does for its layout). Pruned to items still in the inventory tree (`getItemWithIDRecursiv`) once
    there are more than 100. The item record wins over the type record (`RecordFor`).
- `client/TienActionableHotbar_Hotbar.lua`: everything on the hotbar and the menu.
  - Installed at `OnGameStart` (once, `installed` flag; Lua is not always reloaded between games), i.e. after every
    mod's file has loaded, so the wrapper sits outside PAR's replacement whatever the mod order. `ISHotbar` instances
    find methods through the class metatable, so existing hotbars are covered.
  - `activateSlot` wrapper: no record, a joypad, paused, or a slot mismatch → the inner `activateSlot` (PAR's or
    vanilla's). Else the item's menu is built **silently** (`createMenu` with `Mod.silent`, snapshot of every option
    and submenu, `closeAll()` in the same frame, before anything is drawn), the record is matched and the option's
    `onSelect(target, param1..10)` is called exactly like `ISContextMenu:onMouseUp` does (`globalPlayerContext` set
    first). The menu is rebuilt each time so the arguments are current (fluid left, hands, wounds). Not found or
    greyed out (`notAvailable` / `isDisabled`): if the item is in a hand the inner `activateSlot` runs (vanilla puts a
    held item away, so "Equip Primary" toggles naturally: the option is missing while the bat is already primary),
    otherwise a bad halo text names the action. Building the menu clears whatever context menu was open.
  - `createMenu` wrapper (not `OnFillInventoryObjectContextMenu`, so options other mods add in that event are already
    there): for a single item that is on the player's hotbar, append **Change Default Action** with a tooltip saying
    what the slot does now, and two scope submenus, **Every <script display name>** and **Only this <display name>**,
    each starting with "The game's usual action" / "Same as every <type>" (clears that scope) followed by a mirror of
    the item's menu (submenus kept, leaves only, empty submenus dropped). The current choice is ticked; a ticked
    option drops its icon because `ISContextMenu:render` draws the tick where the icon goes. Works in the hotbar's
    right-click and in the inventory window's (the item is on the hotbar there too).
- Translations: `shared/Translate/EN/IG_UI.json` (`IGUI_TienActionableHotbar_*`).
- `scripts/make_art.py`: no text, in the series' sticker style (pixel art scaled by whole numbers, thin dark line +
  white outline one art pixel wide, soft shadow, warm glow on dark). Poster / preview: the whiskey rising out of the
  lit slot 2 of a vanilla-looking hotbar (bat in 1, painkillers in 3), a drawn "2" key cap at its top left and the
  game's Thirst moodle (`Moodles/128/Status_Thirst.png` on `_Moodles_BGsolid.png` tinted good-green) as a badge at
  its bottom right: press 2, drink. Icon: the same bottle, key cap and badge. A first version showed a mock context
  menu with text; the user asked for a better picture. Item icons come from the game's packs: B42 ones
  (Item_Whiskey) in `UI2.pack`, older ones (Item_BaseballBat, Item_PillsPainkiller) only in `UI.pack`; same entry
  format.

## To verify in game

- Bat: Every Baseball Bat > Equip Primary; slot key equips one-handed, second press puts it away. Knife > Equip
  Secondary. Whiskey on a PAR slot > Drink > All; sealed / empty bottles; painkillers > Take Pills.
- Ticks and the tooltip reflect the saved choice; Same as every / game's usual action clear it; the ini and modData
  survive a restart and an MP reconnect (does the server keep the client's `transmitModData`?).
- The silent menu never flashes on screen, and nothing breaks when a context menu was already open.
- With and without PAR; split screen players 1-3 (their hotbars are hidden, keys are player 0 only).
- `FunctionName`'s global scan cost on the first pick of an option from an unknown table.

## Decisions

- Its own mod (the user's choice), client only, no sandbox option: it only changes what the player's own hotbar does,
  and the actions are the ones the player can already click.
- A full copy of the item's context menu rather than a fixed list of actions, so every item and every mod's options
  are covered (user agreed after the attachable-item survey: ~225 back weapons for one-handed equip, ~70 belt weapons
  for the off hand, PAR's ~30 bottles and pills for drink / take pills).
- Both scopes: per type (most useful, follows the player) and per item (overrides).
