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

-- Every saved character as { key, char }: the logged-in one first, the rest
-- by name.
function DB.ListChars()
    local list = {}
    if type(PocketBankDB) ~= "table" or type(PocketBankDB.chars) ~= "table" then return list end
    local current = DB.GetCharKey()
    for key, char in pairs(PocketBankDB.chars) do
        list[#list + 1] = { key = key, char = char }
    end
    table.sort(list, function(a, b)
        if a.key == current then return true end
        if b.key == current then return false end
        local na = a.char.fullName or a.char.name or a.key
        local nb = b.char.fullName or b.char.name or b.key
        return na < nb
    end)
    return list
end

-- The logged-in character can never be deleted: a scan would save it again.
function DB.DeleteChar(key)
    if type(key) ~= "string" or type(PocketBankDB) ~= "table" then return false end
    local chars = PocketBankDB.chars
    if type(chars) ~= "table" or not chars[key] or key == DB.GetCharKey() then return false end
    chars[key] = nil
    PB.FireCallback("CHAR_DELETED", key)
    return true
end

function DB.SaveCharMeta(event)
    local char = DB.GetChar(true)
    if not char then return nil end
    local className, class = UnitClass("player")
    local raceName, race = UnitRace("player")
    char.guid = DB.GetCharKey()
    char.className = className
    char.raceName = raceName
    char.race = race
    char.sex = UnitSex("player")
    -- Forever names have two parts; UnitName returns the second one where
    -- other clients return the realm.
    local name, secondName = UnitName("player")
    char.name = name
    char.secondName = secondName ~= "" and secondName or nil
    char.fullName = char.secondName and (name .. " " .. char.secondName) or name
    char.realm = GetRealmName()
    char.class = class
    char.faction = UnitFactionGroup("player")
    char.level = UnitLevel("player")
    local money = GetMoney()
    if type(PocketBankDB.debug) == "table" and event then
        PocketBankDB.debug.moneyAt = PocketBankDB.debug.moneyAt or {}
        PocketBankDB.debug.moneyAt[event] = money
    end
    -- Saved money went to 0 for every character: GetMoney() is unreliable
    -- while logging out, and the logout save overwrote the good value.
    if event ~= "PLAYER_LOGOUT" then char.money = money end
    char.lastSeen = time()
    return char
end
