local ADDON, PB = ...

-- Diagnostic dump: reports what the client really exposes about bank and bag
-- containers so later code only uses verified API. Results go to the chat
-- (summary) and to PocketBankDB.debug (full, written to disk on /reload).

local Debug = {}
PB.Debug = Debug

local MAX_EVENTS = 60
local EVENTS = {
    "BANKFRAME_OPENED", "BANKFRAME_CLOSED",
    "PLAYERBANKSLOTS_CHANGED", "PLAYERBANKBAGSLOTS_CHANGED",
    "PLAYER_ACCOUNT_BANK_TAB_SLOTS_CHANGED", "BAG_UPDATE_DELAYED",
    "GUILDBANKFRAME_OPENED", "GUILDBANKFRAME_CLOSED", "GUILDBANK_UPDATE_TABS",
    "MAIL_SHOW", "MAIL_CLOSED",
}

local function sortedKeys(t)
    local keys = {}
    for k in pairs(t) do keys[#keys + 1] = tostring(k) end
    table.sort(keys)
    return keys
end

local function describe(v)
    local t = type(v)
    if t == "table" then return "table" end
    return t .. ":" .. tostring(v)
end

local function db()
    PocketBankDB = PocketBankDB or { schemaVersion = 1, chars = {} }
    PocketBankDB.debug = PocketBankDB.debug or { events = {} }
    return PocketBankDB.debug
end

local function collect()
    local out = {}
    local function add(fmt, ...) out[#out + 1] = string.format(fmt, ...) end

    local version, build, buildDate, toc = GetBuildInfo()
    add("build: %s (%s) %s interface=%s", tostring(version), tostring(build), tostring(buildDate), tostring(toc))
    add("locale: %s", tostring(GetLocale()))
    add("bankFrameShown: %s", tostring(BankFrame and BankFrame:IsShown() or false))

    -- Forever uses two-part names and no realms: find which call returns what.
    local function probe(label, fn, ...)
        if type(fn) ~= "function" then add("%s: missing", label) return end
        local results = { pcall(fn, ...) }
        local parts = {}
        for i = 2, #results do parts[#parts + 1] = tostring(results[i]) end
        add("%s: ok=%s -> %s", label, tostring(results[1]), table.concat(parts, " | "))
    end
    probe("UnitName", _G.UnitName, "player")
    probe("UnitFullName", _G.UnitFullName, "player")
    probe("UnitNameUnmodified", _G.UnitNameUnmodified, "player")
    probe("GetUnitName(true)", _G.GetUnitName, "player", true)
    probe("UnitGUID", _G.UnitGUID, "player")
    probe("GetRealmName", _G.GetRealmName)
    probe("GetNormalizedRealmName", _G.GetNormalizedRealmName)
    probe("GetPlayerInfoByGUID", _G.GetPlayerInfoByGUID, _G.UnitGUID and _G.UnitGUID("player"))
    if C_PlayerInfo then add("C_PlayerInfo: %s", table.concat(sortedKeys(C_PlayerInfo), ", ")) end
    add("TooltipDataProcessor: %s", type(TooltipDataProcessor))
    add("Enum.TooltipDataType: %s", type(Enum and Enum.TooltipDataType))

    -- API the next versions depend on: options widgets, mail, currencies,
    -- guild bank, professions and rested XP.
    if type(Settings) == "table" then add("Settings: %s", table.concat(sortedKeys(Settings), ", ")) end
    for _, name in ipairs({ "CreateSettingsButtonInitializer", "CreateSettingsListSectionHeaderInitializer",
        "StaticPopup_Show", "StaticPopupDialogs", "MenuUtil", "GetInboxNumItems", "GetInboxHeaderInfo",
        "GetInboxItem", "GetInboxItemLink", "CheckInbox", "C_Mail", "C_CurrencyInfo", "GetCurrencyListSize",
        "GetCurrencyListInfo", "C_GuildBank", "GetNumGuildBankTabs", "GetGuildBankItemLink",
        "GetGuildBankItemInfo", "GetProfessions", "GetProfessionInfo", "C_TradeSkillUI",
        "GetXPExhaustion", "GetRestState" }) do
        add("%s: %s", name, type(_G[name]))
    end
    for _, name in ipairs({ "C_Mail", "C_CurrencyInfo", "C_GuildBank", "C_TradeSkillUI", "MenuUtil" }) do
        if type(_G[name]) == "table" then add("%s: %s", name, table.concat(sortedKeys(_G[name]), ", ")) end
    end

    for _, name in ipairs({ "BANK_CONTAINER", "REAGENTBANK_CONTAINER", "KEYRING_CONTAINER",
        "NUM_BAG_SLOTS", "NUM_BANKBAGSLOTS", "NUM_BANKGENERIC_SLOTS",
        "NUM_TOTAL_EQUIPPED_BAG_SLOTS", "NUM_TOTAL_BAG_FRAMES" }) do
        add("global %s = %s", name, describe(_G[name]))
    end

    if Enum and Enum.BagIndex then
        for _, k in ipairs(sortedKeys(Enum.BagIndex)) do
            add("Enum.BagIndex.%s = %s", k, tostring(Enum.BagIndex[k]))
        end
    else
        add("Enum.BagIndex: missing")
    end

    if C_Container then
        add("C_Container: %s", table.concat(sortedKeys(C_Container), ", "))
    else
        add("C_Container: missing")
    end
    for _, name in ipairs({ "C_Bank", "C_GuildBank", "C_AccountBank" }) do
        local t = _G[name]
        add("%s: %s", name, t and table.concat(sortedKeys(t), ", ") or "missing")
    end
    for _, name in ipairs({ "GetContainerNumSlots", "GetContainerItemInfo", "GetContainerItemLink",
        "GetNumGuildBankTabs", "GetGuildBankItemInfo", "GetInventoryItemLink", "GetInboxNumItems" }) do
        add("function %s: %s", name, type(_G[name]))
    end

    if C_Container and C_Container.GetContainerNumSlots then
        for id = -5, 14 do
            local ok, n = pcall(C_Container.GetContainerNumSlots, id)
            add("container %d: slots=%s", id, ok and tostring(n) or ("error " .. tostring(n)))
        end
        local sample
        for id = -1, 11 do
            local ok, n = pcall(C_Container.GetContainerNumSlots, id)
            if ok and n and n > 0 and C_Container.GetContainerItemInfo then
                for slot = 1, n do
                    local ok2, info = pcall(C_Container.GetContainerItemInfo, id, slot)
                    if ok2 and info then sample = { id, slot, info }; break end
                end
            end
            if sample then break end
        end
        if sample then
            local info = sample[3]
            local parts = {}
            for _, k in ipairs(sortedKeys(info)) do parts[#parts + 1] = k .. "=" .. describe(info[k]) end
            add("sample item (container %d, slot %d): %s", sample[1], sample[2], table.concat(parts, ", "))
        else
            add("sample item: none found")
        end
    end

    for _, name in ipairs({ "BankFrame", "BankSlotsFrame", "BankFrameItem1", "ContainerFrame1",
        "ContainerFrameCombinedBags", "GuildBankFrame", "MailFrame", "ReagentBankFrame",
        "AccountBankPanel", "BankPanel" }) do
        local f = _G[name]
        if f then
            local w, h = f.GetWidth and f:GetWidth() or 0, f.GetHeight and f:GetHeight() or 0
            add("frame %s: exists %s type=%s size=%.0fx%.0f template=%s", name, tostring(f.IsShown and f:IsShown()),
                tostring(f.GetObjectType and f:GetObjectType()), w, h, tostring(f.GetName and f:GetName()))
        else
            add("frame %s: missing", name)
        end
    end

    return out
end

function Debug.Run()
    local bankOpen = BankFrame and BankFrame:IsShown() or false
    local state = bankOpen and "bankOpen" or "bankClosed"
    local lines = collect()
    local store = db()
    store[state] = { time = date("%Y-%m-%d %H:%M:%S"), lines = lines }
    print(string.format("|cffffd100PocketBank debug|r [%s]: %d lines saved. Type /reload to write them to disk.", state, #lines))
    print(string.format("  C_Container=%s  BankFrame=%s", tostring(C_Container ~= nil), tostring(BankFrame ~= nil)))
end

local function dumpValue(v, depth)
    if type(v) ~= "table" then return tostring(v) end
    if depth <= 0 then return "{...}" end
    local parts = {}
    for _, k in ipairs(sortedKeys(v)) do
        local val = v[k]
        if val == nil then val = v[tonumber(k)] end
        parts[#parts + 1] = k .. "=" .. dumpValue(val, depth - 1)
    end
    return "{" .. table.concat(parts, ", ") .. "}"
end

local function walk(frame, depth, out, indent)
    local function add(fmt, ...) out[#out + 1] = indent .. string.format(fmt, ...) end
    local name = frame.GetName and frame:GetName() or "(anon)"
    local w, h = frame:GetWidth() or 0, frame:GetHeight() or 0
    local point, _, relPoint, x, y = frame:GetPoint(1)
    add("[%s] %s %.0fx%.0f shown=%s point=%s/%s %.0f,%.0f strata=%s", tostring(frame:GetObjectType()), tostring(name), w, h,
        tostring(frame:IsShown()), tostring(point), tostring(relPoint), x or 0, y or 0, tostring(frame:GetFrameStrata()))
    if frame.GetRegions then
        for _, r in ipairs({ frame:GetRegions() }) do
            local t = r:GetObjectType()
            if t == "Texture" then
                add("  tex %s layer=%s atlas=%s file=%s size=%.0fx%.0f", tostring(r:GetName() or "-"), tostring(r:GetDrawLayer()),
                    tostring(r:GetAtlas()), tostring(r:GetTexture()), r:GetWidth() or 0, r:GetHeight() or 0)
            elseif t == "FontString" then
                add("  text %s font=%s %q", tostring(r:GetName() or "-"), tostring(r:GetFontObject() and r:GetFontObject():GetName()), tostring(r:GetText()))
            end
        end
    end
    if depth > 0 and frame.GetChildren then
        local kids = { frame:GetChildren() }
        local shown = 0
        for _, c in ipairs(kids) do
            -- item slots repeat 48 times: show the first few of a kind only
            shown = shown + 1
            if shown <= 40 then walk(c, depth - 1, out, indent .. "  ") end
        end
        if #kids > 40 then add("  ... %d more children", #kids - 40) end
    end
end

function Debug.Frames()
    local out = {}
    local function add(fmt, ...) out[#out + 1] = string.format(fmt, ...) end
    add("BankFrame shown=%s", tostring(BankFrame and BankFrame:IsShown()))
    if C_Bank then
        for _, fn in ipairs({ "FetchViewableBankTypes", "FetchPurchasedBankTabIDs", "FetchPurchasedBankTabData",
            "FetchNumPurchasedBankTabs", "FetchMaxNumBankTabs", "CanViewBank", "CanUseBank" }) do
            local f = C_Bank[fn]
            if f then
                local ok, a, b = pcall(f, Enum and Enum.BankType and Enum.BankType.Character or 0)
                add("C_Bank.%s(Character) -> %s %s %s", fn, tostring(ok), dumpValue(a, 3), dumpValue(b, 2))
                local ok2, a2 = pcall(f, Enum and Enum.BankType and Enum.BankType.Account or 2)
                add("C_Bank.%s(Account) -> %s %s", fn, tostring(ok2), dumpValue(a2, 3))
            end
        end
    end
    if Enum and Enum.BankType then add("Enum.BankType = %s", dumpValue(Enum.BankType, 1)) end
    if C_Container and C_Container.GetContainerNumSlots then
        for id = 6, 23 do add("container %d slots=%s name=%s", id, tostring(C_Container.GetContainerNumSlots(id)),
            tostring(C_Container.GetBagName and C_Container.GetBagName(id))) end
    end
    local root = BankFrame
    if root then walk(root, 4, out, "") end
    local store = db()
    store.frames = { time = date("%Y-%m-%d %H:%M:%S"), lines = out }
    print(string.format("|cffffd100PocketBank frames|r: %d lines saved. Type /reload to write them to disk.", #out))
end

local SLOT_NAMES = {
    "AmmoSlot", "HeadSlot", "NeckSlot", "ShoulderSlot", "ShirtSlot", "ChestSlot", "WaistSlot", "LegsSlot",
    "FeetSlot", "WristSlot", "HandsSlot", "Finger0Slot", "Finger1Slot", "Trinket0Slot", "Trinket1Slot",
    "BackSlot", "MainHandSlot", "SecondaryHandSlot", "RangedSlot", "TabardSlot",
}

-- Character sheet layout and the model API needed to dress an offline
-- character. Open the character window (C) before running it.
function Debug.Paperdoll()
    local out = {}
    local function add(fmt, ...) out[#out + 1] = string.format(fmt, ...) end
    add("CharacterFrame shown=%s", tostring(CharacterFrame and CharacterFrame:IsShown()))
    add("UnitRace: %s", table.concat({ tostringall(UnitRace("player")) }, " | "))
    add("UnitSex: %s", tostring(UnitSex("player")))
    add("UnitClass: %s", table.concat({ tostringall(UnitClass("player")) }, " | "))
    add("LOCALIZED_CLASS_NAMES_MALE: %s", type(LOCALIZED_CLASS_NAMES_MALE))
    add("CHARACTER_LEVEL_TEMPLATE: %s", tostring(_G.CHARACTER_LEVEL_TEMPLATE))
    add("PLAYER_LEVEL: %s", tostring(_G.PLAYER_LEVEL))
    for _, name in ipairs(SLOT_NAMES) do
        local ok, id, texture = pcall(GetInventorySlotInfo, name)
        add("slot %s: ok=%s id=%s texture=%s link=%s", name, tostring(ok), tostring(id), tostring(texture),
            tostring(ok and id and GetInventoryItemLink("player", id)))
    end
    for _, kind in ipairs({ "DressUpModel", "PlayerModel", "ModelScene" }) do
        local ok, model = pcall(CreateFrame, kind, nil, UIParent)
        if ok and model then
            local methods = {}
            for _, m in ipairs({ "SetUnit", "SetCustomRace", "Undress", "TryOn", "Dress", "SetSheathed",
                "SetPortraitZoom", "SetCamDistanceScale", "SetPosition", "SetFacing", "RefreshUnit",
                "SetModelByUnit", "SetItemTransmogInfo", "GetItemTransmogInfoList", "SetAutoDress",
                "SetDoBlend", "SetKeepModelOnHide", "GetPlayerActor", "CreateActor" }) do
                if type(model[m]) == "function" then methods[#methods + 1] = m end
            end
            add("%s: %s", kind, table.concat(methods, ", "))
            -- Full method list, to look for another way to load a race model.
            local function allMethods(object)
                local mt = getmetatable(object)
                local index = mt and mt.__index
                return type(index) == "table" and table.concat(sortedKeys(index), ", ") or "?"
            end
            add("%s all: %s", kind, allMethods(model))
            if kind == "ModelScene" and model.CreateActor then
                local okActor, actor = pcall(model.CreateActor, model)
                add("ModelSceneActor all: %s", okActor and actor and allMethods(actor) or tostring(actor))
            end
            model:Hide()
        else
            add("%s: cannot create (%s)", kind, tostring(model))
        end
    end
    for _, name in ipairs({ "PaperDollFrame", "CharacterModelScene", "CharacterModelFrame", "PaperDollItemsFrame",
        "CharacterHeadSlot", "CharacterMainHandSlot", "CharacterRangedSlot", "CharacterLevelText" }) do
        add("frame %s: %s", name, _G[name] and "exists" or "missing")
    end
    if CharacterFrame then walk(CharacterFrame, 4, out, "") end
    local store = db()
    store.paperdoll = { time = date("%Y-%m-%d %H:%M:%S"), lines = out }
    print(string.format("|cffffd100PocketBank paperdoll|r: %d lines saved. Type /reload to write them to disk.", #out))
end

local frame = CreateFrame("Frame")
for _, ev in ipairs(EVENTS) do pcall(frame.RegisterEvent, frame, ev) end
frame:SetScript("OnEvent", function(_, event, ...)
    local store = db()
    local list = store.events
    list[#list + 1] = {
        t = date("%H:%M:%S"), event = event, args = (select("#", ...) > 0) and strjoin(",", tostringall(...)) or "",
    }
    if #list > MAX_EVENTS then table.remove(list, 1) end
end)
