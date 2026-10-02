# Tien's Actionable Hotbar

Choose what each hotbar slot does. Clicking a slot or pressing its number key normally equips the item, or switches it
on and off. With this mod it can do any action from the item's own right-click menu instead.

- **Any action from the item's menu.** Right-click an item on the hotbar (or in your inventory, while it is on the
  hotbar) > **Change Default Action**, and pick from a copy of that item's menu. For example:
  - a baseball bat, axe or shovel: **Equip Primary**, to swing it with one hand and keep the other hand free;
  - a knife on the belt: **Equip Secondary**;
  - whiskey or a water bottle on your webbing: **Drink > All** (or Half, or Quarter);
  - painkillers: **Take Pills**.
- **For every item of that kind, or just this one.** **Every Whiskey** applies to every bottle of whiskey you carry, now
  and later. **Only this Whiskey** applies to that one bottle and wins over the "every" setting.
- **Back to normal at any time.** Pick **The game's usual action** in the same menu.
- **Press again to put it away.** When the action can't be done (for example, "Equip Primary" while the bat is already
  in your hand), pressing the slot does the usual thing instead, which puts a held item away. Otherwise a short message
  over your head says the action can't be done right now.
- **Works with other mods.** Actions that other mods add to an item's menu can be picked too. Mods that make more items
  attachable, such as Plysken Attachments Reborn (bottles, pills, first aid kits...), work as well.

## Where it is saved

- **Every ...** settings are saved on your computer (`Zomboid/Lua/TienActionableHotbar.ini`), so they follow you to every
  save and server.
- **Only this ...** settings belong to the character (saved with the character, and on the server in multiplayer).

Build 42 only. It only changes what your own hotbar does; the actions themselves are the game's own. In multiplayer the
server needs it in its mod list like any other mod.
