"""Simulated-client checks for the PocketBank saved data and bank scanner."""

import sys
from pathlib import Path

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parent.parent

RUNTIME_FILES = [
    "Locales/Locale.lua",
    "Locales/enUS.lua",
    "Locales/esES.lua",
    "Core/Init.lua",
    "Core/DB.lua",
    "Modules/BankScan.lua",
]

ALL_LUA = sorted(
    path.relative_to(ROOT).as_posix()
    for folder in ("Core", "Locales", "Modules")
    for path in (ROOT / folder).glob("*.lua")
)

CHAR = 'PocketBankDB.chars["Realm-Name"]'

HARNESS = r"""
PB = {}
CHAT = {}
TIMERS = {}
FRAMES = {}
BANK = {}

function print(...)
    local parts = {}
    for i = 1, select("#", ...) do parts[i] = tostring((select(i, ...))) end
    CHAT[#CHAT + 1] = table.concat(parts, " ")
end

function CountKeys(t)
    local n = 0
    for _ in pairs(t or {}) do n = n + 1 end
    return n
end

function GetLocale() return "enUS" end
function GetRealmName() return "Realm" end
function UnitName(unit) return "Name" end
function UnitClass(unit) return "Warrior", "WARRIOR" end
function UnitFactionGroup(unit) return "Alliance" end
function UnitLevel(unit) return 60 end
function GetMoney() return 12345 end
function time() return 1700000000 end

Enum = { BagIndex = {}, BankType = { Character = 0, Account = 1 } }
for i = 1, 9 do Enum.BagIndex["CharacterBankTab_" .. i] = 5 + i end

C_Container = {}
function C_Container.GetContainerNumSlots(id)
    local tab = BANK[id]
    return tab and tab.size or 0
end
function C_Container.GetContainerItemInfo(id, slot)
    local tab = BANK[id]
    return tab and tab.items and tab.items[slot] or nil
end

C_Bank = {}
function C_Bank.FetchPurchasedBankTabIDs(kind)
    return BANK.tabIDs or {}
end
function C_Bank.FetchPurchasedBankTabData(kind)
    return BANK.tabData or {}
end

C_Timer = {}
function C_Timer.After(delay, fn)
    TIMERS[#TIMERS + 1] = { delay = delay, fn = fn }
end

function RunTimers()
    local list = TIMERS
    TIMERS = {}
    for _, timer in ipairs(list) do timer.fn() end
end

function CreateFrame(kind)
    local frame = { events = {}, scripts = {} }
    function frame:RegisterEvent(event) self.events[event] = true end
    function frame:UnregisterEvent(event) self.events[event] = nil end
    function frame:SetScript(name, fn) self.scripts[name] = fn end
    FRAMES[#FRAMES + 1] = frame
    return frame
end

function FireEvent(event, ...)
    for _, frame in ipairs(FRAMES) do
        if frame.events[event] and frame.scripts.OnEvent then
            frame.scripts.OnEvent(frame, event, ...)
        end
    end
end

SlashCmdList = {}
C_AddOns = { GetAddOnMetadata = function(_, field) return field == "Version" and "dev" or nil end }
function strlower(s) return string.lower(s) end
function strtrim(s) return (s:gsub("^%s*(.-)%s*$", "%1")) end

function Item(id, count, quality)
    return {
        itemID = id,
        itemName = "Item " .. id,
        hyperlink = "|cff9d9d9d|Hitem:" .. id .. "|h[Item " .. id .. "]|h|r",
        iconFileID = 1000 + id,
        quality = quality or 1,
        stackCount = count or 1,
        isBound = false,
    }
end

function SetBank(size, items)
    BANK = {}
    BANK.tabIDs = { 6 }
    BANK.tabData = { { ID = 6, name = "Bank", icon = 134400 } }
    BANK[6] = { size = size, items = items or {} }
end
"""

failures = []


def check(condition, message):
    print(("PASS " if condition else "FAIL ") + message)
    if not condition:
        failures.append(message)


def new_state():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(HARNESS)
    return lua


def boot(scenario=""):
    """Load the addon files in .toc order on a fresh fake client."""
    lua = new_state()
    pb = lua.globals().PB
    for name in RUNTIME_FILES:
        source = (ROOT / name).read_text(encoding="utf-8")
        chunk = lua.eval("loadstring")(source, name)
        if chunk is None:
            raise SystemExit(f"cannot load {name}")
        chunk("PocketBank", pb)
    if scenario:
        lua.execute(scenario)
    return lua


def value(lua, expression):
    return lua.eval("function() return " + expression + " end")()


def check_compiles():
    lua = new_state()
    loadstring = lua.eval("loadstring")
    for name in ALL_LUA:
        source = (ROOT / name).read_text(encoding="utf-8")
        check(loadstring(source, name) is not None, f"{name} compiles")


def test_populated_bank():
    lua = boot(
        'SetBank(8, { [1] = Item(1234, 5, 2), [2] = Item(5678, 1, 4), [5] = Item(42, 20, 1) })'
        "SCANNED = 0\n"
        'PB.RegisterCallback("BANK_SCANNED", function(char) SCANNED = SCANNED + 1 end)'
        'FireEvent("ADDON_LOADED", "PocketBank")'
        'FireEvent("PLAYER_LOGIN")'
        'FireEvent("BANKFRAME_OPENED")'
    )
    check(value(lua, "#TIMERS") == 1, "opening the bank schedules one scan")
    lua.execute('FireEvent("BAG_UPDATE_DELAYED")')
    check(value(lua, "#TIMERS") == 1, "change events debounce into the pending scan")
    lua.execute("RunTimers()")

    check(value(lua, "PocketBankDB ~= nil") is True, "ADDON_LOADED creates PocketBankDB")
    check(value(lua, "PocketBankDB.schemaVersion") == 1, "schemaVersion is 1")
    check(value(lua, f"{CHAR} ~= nil") is True, "character stored under Realm-Name")
    check(value(lua, f'{CHAR}.name == "Name" and {CHAR}.realm == "Realm"'),
          "character name and realm saved")
    check(value(lua, f'{CHAR}["class"]') == "WARRIOR", "class saved")
    check(value(lua, f"{CHAR}.faction") == "Alliance", "faction saved")
    check(value(lua, f"{CHAR}.level") == 60, "level saved")
    check(value(lua, f"{CHAR}.money") == 12345, "money saved")
    check(value(lua, f"{CHAR}.lastSeen") == 1700000000, "lastSeen saved")

    check(value(lua, f"{CHAR}.bank.scanned") == 1700000000, "bank.scanned saved")
    check(value(lua, f"CountKeys({CHAR}.bank.tabs)") == 1, "one bank tab stored")
    tab = f"{CHAR}.bank.tabs[1]"
    check(value(lua, f"{tab}.id") == 6, "tab id comes from the purchased tabs")
    check(value(lua, f'{tab}.name == "Bank" and {tab}.icon == 134400'), "tab name and icon saved")
    check(value(lua, f"{tab}.size") == 8, "tab size saved")
    check(value(lua, f"CountKeys({tab}.items)") == 3, "three items stored, empty slots skipped")
    check(value(lua, f'{tab}.items[1].id == 1234 and {tab}.items[1].count == 5'), "slot 1 item saved")
    check(value(lua, f'{tab}.items[2].id == 5678 and {tab}.items[2].quality == 4'), "slot 2 item saved")
    check(value(lua, f'{tab}.items[5].id == 42 and {tab}.items[5].count == 20'), "slot 5 item saved")
    check(value(lua, f'{tab}.items[1].link ~= nil and {tab}.items[1].icon == 2234'),
          "item link and icon saved")

    check(value(lua, "#CHAT") == 1, "chat message printed once on open")
    check(value(lua, "CHAT[1]") == "Bank saved (3 items).", "chat message reports the item count")
    check(value(lua, "SCANNED") == 1, "BANK_SCANNED fires after the first scan")

    lua.execute('BANK[6].items[1] = nil; FireEvent("PLAYERBANKSLOTS_CHANGED"); RunTimers()')
    check(value(lua, f"CountKeys({tab}.items)") == 2,
          "change event rescans and replaces the saved contents")
    check(value(lua, "#CHAT") == 1, "later scans in the same open do not print again")
    check(value(lua, "SCANNED") == 2, "BANK_SCANNED fires after each rescan")

    lua.execute('FireEvent("BANKFRAME_CLOSED"); FireEvent("BAG_UPDATE_DELAYED")')
    check(value(lua, "#TIMERS") == 0, "no scan is scheduled while the bank is closed")


def test_empty_bank():
    lua = boot(
        'SetBank(0, {})'
        'FireEvent("ADDON_LOADED", "PocketBank")'
        'FireEvent("BANKFRAME_OPENED")'
        'RunTimers()'
    )
    tab = f"{CHAR}.bank.tabs[1]"
    check(value(lua, f"{tab}.size") == 0, "empty bank keeps a tab with size 0")
    check(value(lua, f"CountKeys({tab}.items)") == 0, "empty bank stores no items")
    check(value(lua, "CHAT[1]") == "Bank saved (0 items).", "empty bank reports 0 items")


def test_debug_key_survives_init():
    lua = boot(
        'PocketBankDB = { debug = { events = { "kept" } } }'
        "PB.DB.Init()"
        "PB.DB.Init()"
    )
    check(value(lua, 'PocketBankDB.debug.events[1]') == "kept", "debug key survives Init")
    check(value(lua, "PocketBankDB.schemaVersion") == 1, "Init migrates the store to schemaVersion 1")
    check(value(lua, "type(PocketBankDB.chars)") == "table", "Init creates the chars table")

    lua.execute(f'{CHAR} = {{ name = "Name", bank = {{ tabs = {{}} }} }}; PB.DB.Init()')
    check(value(lua, f"{CHAR} ~= nil") is True, "Init keeps existing characters")


def main():
    check_compiles()
    test_populated_bank()
    test_empty_bank()
    test_debug_key_survives_init()
    if failures:
        print(f"\n{len(failures)} check(s) failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
