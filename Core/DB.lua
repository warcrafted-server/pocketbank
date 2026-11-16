local ADDON, PB = ...

local DB = {}
PB.DB = DB

local SCHEMA_VERSION = 2

-- Entries migrate the saved data from version N-1 to N. They edit the store in
-- place so keys owned by other modules (debug) are never dropped.
local MIGRATIONS = {
    function(store) store.chars = store.chars or {} end,
    -- Forever has no realms: GetRealmName() returns a technical server name that
    -- may change, so characters are keyed by GUID. Version 1 only existed in
    -- development builds, so its entries are dropped instead of converted.
    function(store)
        for key in pairs(store.chars) do
            if not string.find(key, "^Player%-") then store.chars[key] = nil end
        end
    end,
}

function DB.Init()
    local store = type(PocketBankDB) == "table" and PocketBankDB or {}
    local version = tonumber(store.schemaVersion) or 0
    if version < SCHEMA_VERSION then
        for target = version + 1, SCHEMA_VERSION do
            local migrate = MIGRATIONS[target]
            if migrate then migrate(store) end
        end
        store.schemaVersion = SCHEMA_VERSION
    end
    if type(store.chars) ~= "table" then store.chars = {} end
    PocketBankDB = store
    return store
end

function DB.GetCharKey()
    return UnitGUID("player")
end

function DB.GetChar(create)
    if type(PocketBankDB) ~= "table" then DB.Init() end
    local key = DB.GetCharKey()
    if not key then return nil end
    local char = PocketBankDB.chars[key]
    if not char and create then
        char = { guid = key, name = UnitName("player"), realm = GetRealmName() }
        PocketBankDB.chars[key] = char
    end
    return char
end

function DB.GetCharByKey(key)
    return type(PocketBankDB) == "table" and PocketBankDB.chars and PocketBankDB.chars[key] or nil
end

function DB.SaveCharMeta()
    local char = DB.GetChar(true)
    if not char then return nil end
    local _, class = UnitClass("player")
    char.guid = DB.GetCharKey()
    char.name = UnitName("player")
    char.realm = GetRealmName()
    char.class = class
    char.faction = UnitFactionGroup("player")
    char.level = UnitLevel("player")
    char.money = GetMoney()
    char.lastSeen = time()
    return char
end
