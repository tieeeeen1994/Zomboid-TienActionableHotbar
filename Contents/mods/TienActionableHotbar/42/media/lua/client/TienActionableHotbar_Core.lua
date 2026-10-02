TienActionableHotbar = TienActionableHotbar or {}

local Mod = TienActionableHotbar

Mod.FILE = "TienActionableHotbar.ini"
Mod.VERSION = 1
Mod.MODDATA = "TienActionableHotbar"
Mod.MAX_ITEM_RECORDS = 100
Mod.MAX_DEPTH = 6
Mod.PARAMS = 10
Mod.SCOPE_TYPE = "type"
Mod.SCOPE_ITEM = "item"

Mod.types = nil
Mod.silent = false

local FIRST_TABLES = { "ISInventoryPaneContextMenu", "ISHotbar", "ISWorldObjectContextMenu", "ISTimedActionQueue" }
local functionNames = {}

local function clean(text)
    return (string.gsub(text, "[\r\n]", " "))
end

function Mod.EncodeParam(value)
    local kind = type(value)
    if kind == "number" or kind == "boolean" then
        return string.sub(kind, 1, 1) .. ":" .. tostring(value)
    end
    if kind == "string" and not string.find(value, "[\r\n]") then
        return "s:" .. value
    end
    return nil
end

function Mod.CopyRecord(rec)
    if type(rec) ~= "table" or type(rec.path) ~= "table" then
        return nil
    end
    local out = { path = {}, params = {} }
    if type(rec.fn) == "string" and rec.fn ~= "" then
        out.fn = rec.fn
    end
    for i, name in ipairs(rec.path) do
        out.path[i] = tostring(name)
    end
    if type(rec.params) == "table" then
        for index, code in pairs(rec.params) do
            local n = tonumber(index)
            if n and type(code) == "string" then
                out.params[n] = code
            end
        end
    end
    if #out.path == 0 then
        return nil
    end
    return out
end

function Mod.Label(rec)
    return table.concat(rec.path, " > ")
end

function Mod.Load()
    local types = {}
    local reader = getFileReader(Mod.FILE, false)
    if reader then
        local current = nil
        local line = reader:readLine()
        while line do
            local key, value = string.match(line, "^(%a+)=(.*)$")
            if key == "item" then
                current = nil
                if value ~= "" then
                    current = { path = {}, params = {} }
                    types[value] = current
                end
            elseif current and key == "fn" then
                current.fn = value
            elseif current and key == "param" then
                local index, code = string.match(value, "^(%d+):(.+)$")
                if index then
                    current.params[tonumber(index)] = code
                end
            elseif current and key == "path" then
                table.insert(current.path, value)
            end
            line = reader:readLine()
        end
        reader:close()
    end
    Mod.types = {}
    for fullType, rec in pairs(types) do
        Mod.types[fullType] = Mod.CopyRecord(rec)
    end
end

function Mod.EnsureLoaded()
    if not Mod.types then
        Mod.Load()
    end
end

function Mod.Save()
    Mod.EnsureLoaded()
    local writer = getFileWriter(Mod.FILE, true, false)
    if not writer then
        return
    end
    writer:write("version=" .. tostring(Mod.VERSION) .. "\n")
    local keys = {}
    for fullType in pairs(Mod.types) do
        table.insert(keys, fullType)
    end
    table.sort(keys)
    for _, fullType in ipairs(keys) do
        local rec = Mod.types[fullType]
        writer:write("item=" .. fullType .. "\n")
        if rec.fn then
            writer:write("fn=" .. rec.fn .. "\n")
        end
        for index = 1, Mod.PARAMS do
            if rec.params[index] then
                writer:write("param=" .. string.format("%d", index) .. ":" .. rec.params[index] .. "\n")
            end
        end
        for _, name in ipairs(rec.path) do
            writer:write("path=" .. name .. "\n")
        end
    end
    writer:close()
end

function Mod.GetTypeRecord(fullType)
    Mod.EnsureLoaded()
    return Mod.CopyRecord(Mod.types[fullType])
end

function Mod.SetTypeRecord(fullType, rec)
    Mod.EnsureLoaded()
    Mod.types[fullType] = Mod.CopyRecord(rec)
    Mod.Save()
end

local function itemStore(player, create)
    local modData = player:getModData()
    local store = modData[Mod.MODDATA]
    if type(store) ~= "table" then
        store = nil
        if create then
            store = {}
            modData[Mod.MODDATA] = store
        end
    end
    return store
end

local function itemKey(item)
    return string.format("%d", item:getID())
end

local function prune(player, store)
    local count = 0
    for _ in pairs(store) do
        count = count + 1
    end
    if count <= Mod.MAX_ITEM_RECORDS then
        return
    end
    local inventory = player:getInventory()
    local stale = {}
    for key in pairs(store) do
        local id = tonumber(key)
        if not id or not inventory:getItemWithIDRecursiv(id) then
            table.insert(stale, key)
        end
    end
    for _, key in ipairs(stale) do
        store[key] = nil
    end
end

function Mod.GetItemRecord(player, item)
    local store = itemStore(player, false)
    if not store then
        return nil
    end
    return Mod.CopyRecord(store[itemKey(item)])
end

function Mod.SetItemRecord(player, item, rec)
    local store = itemStore(player, true)
    store[itemKey(item)] = Mod.CopyRecord(rec)
    prune(player, store)
    if isClient() then
        player:transmitModData()
    end
end

function Mod.RecordFor(player, item)
    local rec = Mod.GetItemRecord(player, item)
    if rec then
        return rec, Mod.SCOPE_ITEM
    end
    rec = Mod.GetTypeRecord(item:getFullType())
    if rec then
        return rec, Mod.SCOPE_TYPE
    end
    return nil, nil
end

local function keyOf(tbl, fn)
    for key, value in pairs(tbl) do
        if value == fn and type(key) == "string" then
            return key
        end
    end
    return nil
end

local function searchGlobals(fn)
    local found = nil
    pcall(function()
        for name, value in pairs(_G) do
            if type(name) == "string" then
                if value == fn then
                    found = name
                    return
                end
                if type(value) == "table" then
                    local key = keyOf(value, fn)
                    if key then
                        found = name .. "." .. key
                        return
                    end
                end
            end
        end
    end)
    return found
end

function Mod.FunctionName(fn)
    if fn == nil then
        return nil
    end
    local cached = functionNames[fn]
    if cached ~= nil then
        return cached or nil
    end
    local name = nil
    for _, tableName in ipairs(FIRST_TABLES) do
        local tbl = _G[tableName]
        if type(tbl) == "table" then
            local key = keyOf(tbl, fn)
            if key then
                name = tableName .. "." .. key
                break
            end
        end
    end
    if not name then
        name = searchGlobals(fn)
    end
    functionNames[fn] = name or false
    return name
end

function Mod.ResolveFunction(name)
    if not name then
        return nil
    end
    local tableName, key = string.match(name, "^([^%.]+)%.(.+)$")
    if not tableName then
        return _G[name]
    end
    local tbl = _G[tableName]
    if type(tbl) ~= "table" then
        return nil
    end
    return tbl[key]
end

local function snapshotMenu(menu, path, depth, leaves, nodes, skip)
    for _, option in ipairs(menu.options) do
        local name = option.name
        if type(name) == "string" and name ~= "" and not (skip and skip[name]) then
            local optionPath = {}
            for i, part in ipairs(path) do
                optionPath[i] = part
            end
            table.insert(optionPath, clean(name))
            if option.subOption then
                local sub = menu:getSubMenu(option.subOption)
                if sub and depth < Mod.MAX_DEPTH then
                    local children = {}
                    snapshotMenu(sub, optionPath, depth + 1, leaves, children, nil)
                    if #children > 0 then
                        table.insert(nodes, {
                            name = name,
                            children = children,
                            iconTexture = option.iconTexture,
                            itemForTexture = option.itemForTexture,
                        })
                    end
                end
            elseif option.onSelect then
                local params = {}
                for i = 1, Mod.PARAMS do
                    params[i] = option["param" .. i]
                end
                local leaf = {
                    name = name,
                    path = optionPath,
                    onSelect = option.onSelect,
                    target = option.target,
                    params = params,
                    available = not option.notAvailable and not option.isDisabled,
                    iconTexture = option.iconTexture,
                    itemForTexture = option.itemForTexture,
                }
                table.insert(leaves, leaf)
                table.insert(nodes, leaf)
            end
        end
    end
end

function Mod.Snapshot(menu, skip)
    local leaves, nodes = {}, {}
    snapshotMenu(menu, {}, 1, leaves, nodes, skip)
    return leaves, nodes
end

function Mod.RecordFromLeaf(leaf)
    local rec = { path = {}, params = {}, fn = Mod.FunctionName(leaf.onSelect) }
    for i, part in ipairs(leaf.path) do
        rec.path[i] = part
    end
    for i = 1, Mod.PARAMS do
        rec.params[i] = Mod.EncodeParam(leaf.params[i])
    end
    return rec
end

local function samePath(leaf, rec)
    if #leaf.path ~= #rec.path then
        return false
    end
    for i = 1, #rec.path do
        if leaf.path[i] ~= rec.path[i] then
            return false
        end
    end
    return true
end

local function sameParams(leaf, rec)
    for index, code in pairs(rec.params) do
        if Mod.EncodeParam(leaf.params[index]) ~= code then
            return false
        end
    end
    return true
end

function Mod.Match(leaves, rec)
    if not rec then
        return nil
    end
    local fn = Mod.ResolveFunction(rec.fn)
    for _, leaf in ipairs(leaves) do
        if samePath(leaf, rec) and (not fn or leaf.onSelect == fn) then
            return leaf
        end
    end
    if not fn then
        return nil
    end
    local lastName = rec.path[#rec.path]
    local count, only, byParams, byName = 0, nil, nil, nil
    for _, leaf in ipairs(leaves) do
        if leaf.onSelect == fn then
            count = count + 1
            only = leaf
            local params = sameParams(leaf, rec)
            local named = leaf.path[#leaf.path] == lastName
            if params and named then
                return leaf
            end
            if params and not byParams then
                byParams = leaf
            end
            if named and not byName then
                byName = leaf
            end
        end
    end
    if byParams then
        return byParams
    end
    if byName then
        return byName
    end
    if count == 1 then
        return only
    end
    return nil
end
