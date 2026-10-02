require "TienActionableHotbar_Core"

local Mod = TienActionableHotbar

local Hotbar = {}
Mod.Hotbar = Hotbar

local function log(message)
    print("[TienActionableHotbar] " .. tostring(message))
end

local function isPaused()
    local speed = UIManager.getSpeedControls()
    return speed ~= nil and speed:getCurrentGameSpeed() == 0
end

function Hotbar.Skip()
    return { [getText("IGUI_TienActionableHotbar_ChangeDefault")] = true }
end

function Hotbar.AttachedItem(playerNum, items)
    if type(items) ~= "table" then
        return nil
    end
    local actual = ISInventoryPane.getActualItems(items)
    if #actual ~= 1 then
        return nil
    end
    local item = actual[1]
    local hotbar = getPlayerHotbar(playerNum)
    if not hotbar or not hotbar:isInHotbar(item) or item:getAttachedSlot() == -1 then
        return nil
    end
    return item
end

function Hotbar.BuildLeaves(playerNum, item)
    Mod.silent = true
    local ok, err = pcall(ISInventoryPaneContextMenu.createMenu, playerNum, true, { item }, getMouseX(), getMouseY())
    Mod.silent = false
    local context = getPlayerContextMenu(playerNum)
    local leaves = {}
    if ok and context then
        leaves = Mod.Snapshot(context, Hotbar.Skip())
    end
    if context then
        context:closeAll()
    end
    if not ok then
        log(err)
    end
    return leaves
end

function Hotbar.Run(playerNum, leaf)
    local p = leaf.params
    ISContextMenu.globalPlayerContext = playerNum
    leaf.onSelect(leaf.target, p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10])
end

function Hotbar.Activate(hotbar, slotIndex, inner)
    local item = hotbar.attachedItems and hotbar.attachedItems[slotIndex]
    if not item or item:getAttachedSlot() ~= slotIndex or JoypadState.players[hotbar.playerNum + 1] or isPaused() then
        return inner(hotbar, slotIndex)
    end
    local player = hotbar.chr
    local rec = Mod.RecordFor(player, item)
    if not rec then
        return inner(hotbar, slotIndex)
    end
    local leaf = Mod.Match(Hotbar.BuildLeaves(hotbar.playerNum, item), rec)
    if leaf and leaf.available then
        Hotbar.Run(hotbar.playerNum, leaf)
        return
    end
    if player:isHandItem(item) then
        return inner(hotbar, slotIndex)
    end
    HaloTextHelper.addBadText(player, getText("IGUI_TienActionableHotbar_CantNow", Mod.Label(rec)))
end

function Hotbar.OnPick(_, playerNum, item, scope, leaf)
    local player = getSpecificPlayer(playerNum)
    if not player or not item then
        return
    end
    local rec = nil
    if leaf then
        rec = Mod.RecordFromLeaf(leaf)
    end
    if scope == Mod.SCOPE_TYPE then
        Mod.SetTypeRecord(item:getFullType(), rec)
    else
        Mod.SetItemRecord(player, item, rec)
    end
    local now = Mod.RecordFor(player, item)
    if now then
        HaloTextHelper.addText(player, getText("IGUI_TienActionableHotbar_Set", Mod.Label(now)))
    else
        HaloTextHelper.addText(player, getText("IGUI_TienActionableHotbar_SetGame"))
    end
end

function Hotbar.Tooltip(itemRec, typeRec, typeName)
    local tooltip = ISInventoryPaneContextMenu.addToolTip()
    if itemRec then
        tooltip.description = getText("IGUI_TienActionableHotbar_NowThis", Mod.Label(itemRec))
    elseif typeRec then
        tooltip.description = getText("IGUI_TienActionableHotbar_NowEvery", Mod.Label(typeRec), typeName)
    else
        tooltip.description = getText("IGUI_TienActionableHotbar_NowGame")
    end
    return tooltip
end

function Hotbar.Mirror(menu, nodes, playerNum, item, scope, checkedLeaf)
    for _, node in ipairs(nodes) do
        local option
        if node.children then
            option = menu:addOption(node.name, nil, nil)
            local sub = menu:getNew(menu)
            menu:addSubMenu(option, sub)
            Hotbar.Mirror(sub, node.children, playerNum, item, scope, checkedLeaf)
        else
            option = menu:addOption(node.name, nil, Hotbar.OnPick, playerNum, item, scope, node)
        end
        if node == checkedLeaf then
            menu:setOptionChecked(option, true)
        else
            option.iconTexture = node.iconTexture
            option.itemForTexture = node.itemForTexture
        end
    end
end

function Hotbar.AddScope(menu, title, checked, firstTitle, firstChecked, nodes, playerNum, item, scope, checkedLeaf)
    local option = menu:addOption(title, nil, nil)
    if checked then
        menu:setOptionChecked(option, true)
    end
    local sub = menu:getNew(menu)
    menu:addSubMenu(option, sub)
    local first = sub:addOption(firstTitle, nil, Hotbar.OnPick, playerNum, item, scope, nil)
    if firstChecked then
        sub:setOptionChecked(first, true)
    end
    Hotbar.Mirror(sub, nodes, playerNum, item, scope, checkedLeaf)
end

function Hotbar.AddMenu(playerNum, items)
    local item = Hotbar.AttachedItem(playerNum, items)
    if not item then
        return
    end
    local context = getPlayerContextMenu(playerNum)
    local player = getSpecificPlayer(playerNum)
    if not context or not player or not context:getIsVisible() then
        return
    end
    local leaves, nodes = Mod.Snapshot(context, Hotbar.Skip())
    if #leaves == 0 then
        return
    end
    local itemRec = Mod.GetItemRecord(player, item)
    local typeRec = Mod.GetTypeRecord(item:getFullType())
    local typeName = item:getScriptItem():getDisplayName()

    local main = context:addOption(getText("IGUI_TienActionableHotbar_ChangeDefault"), nil, nil)
    main.toolTip = Hotbar.Tooltip(itemRec, typeRec, typeName)
    local menu = context:getNew(context)
    context:addSubMenu(main, menu)

    Hotbar.AddScope(menu, getText("IGUI_TienActionableHotbar_Every", typeName), typeRec ~= nil and itemRec == nil,
        getText("IGUI_TienActionableHotbar_GameDefault"), typeRec == nil,
        nodes, playerNum, item, Mod.SCOPE_TYPE, Mod.Match(leaves, typeRec))

    local inheritTitle = getText("IGUI_TienActionableHotbar_GameDefault")
    if typeRec then
        inheritTitle = getText("IGUI_TienActionableHotbar_SameAsEvery", typeName)
    end
    Hotbar.AddScope(menu, getText("IGUI_TienActionableHotbar_ThisOnly", item:getDisplayName()), itemRec ~= nil,
        inheritTitle, itemRec == nil,
        nodes, playerNum, item, Mod.SCOPE_ITEM, Mod.Match(leaves, itemRec))
end

local installed = false

local function install()
    if installed then
        return
    end
    installed = true
    Mod.EnsureLoaded()

    local innerActivate = ISHotbar.activateSlot
    function ISHotbar:activateSlot(slotIndex)
        return Hotbar.Activate(self, slotIndex, innerActivate)
    end

    local innerCreateMenu = ISInventoryPaneContextMenu.createMenu
    ISInventoryPaneContextMenu.createMenu = function(player, isInPlayerInventory, items, x, y, origin, ...)
        local context = innerCreateMenu(player, isInPlayerInventory, items, x, y, origin, ...)
        if not Mod.silent and isInPlayerInventory then
            local ok, err = pcall(Hotbar.AddMenu, player, items)
            if not ok then
                log(err)
            end
        end
        return context
    end
end

Events.OnGameStart.Add(install)
