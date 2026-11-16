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
