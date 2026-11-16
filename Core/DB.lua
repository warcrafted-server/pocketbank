local ADDON, PB = ...

local DB = {}
PB.DB = DB

local SCHEMA_VERSION = 1

-- Entries migrate the saved data from version N-1 to N. They edit the store in
-- place so keys owned by other modules (debug) are never dropped.
local MIGRATIONS = {
    function(store) store.chars = store.chars or {} end,
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
    return GetRealmName() .. "-" .. UnitName("player")
end

function DB.GetChar(create)
    if type(PocketBankDB) ~= "table" then DB.Init() end
    local key = DB.GetCharKey()
    local char = PocketBankDB.chars[key]
    if not char and create then
        char = { name = UnitName("player"), realm = GetRealmName() }
        PocketBankDB.chars[key] = char
    end
    return char
end

function DB.SaveCharMeta()
    local char = DB.GetChar(true)
    local _, class = UnitClass("player")
    char.name = UnitName("player")
    char.realm = GetRealmName()
    char.class = class
    char.faction = UnitFactionGroup("player")
    char.level = UnitLevel("player")
    char.money = GetMoney()
    char.lastSeen = time()
    return char
end
