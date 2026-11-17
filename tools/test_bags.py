"""Simulated-client checks for the PocketBank bag scanner."""

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
    "Modules/BagScan.lua",
]

ALL_LUA = sorted(
    path.relative_to(ROOT).as_posix()
    for folder in ("Core", "Locales", "Modules")
    for path in (ROOT / folder).glob("*.lua")
)

CHAR = 'PocketBankDB.chars["Player-1-0001"]'
TABS = f"{CHAR}.bags.tabs"

HARNESS = r"""
PB = {}
CHAT = {}
TIMERS = {}
FRAMES = {}
BAGS = {}
READS = {}

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
function UnitGUID(unit) return "Player-1-0001" end
function UnitClass(unit) return "Warrior", "WARRIOR" end
function UnitFactionGroup(unit) return "Alliance" end
function UnitLevel(unit) return 60 end
function GetMoney() return 12345 end
function time() return 1700000000 end

Enum = { BagIndex = { Backpack = 0, Bag_1 = 1, Bag_2 = 2, Bag_3 = 3, Bag_4 = 4, ReagentBag = 5 } }

C_Container = {}
function C_Container.GetContainerNumSlots(id)
    READS[#READS + 1] = id
    local bag = BAGS[id]
    return bag and bag.size or 0
end
function C_Container.GetContainerItemInfo(id, slot)
    READS[#READS + 1] = id
    local bag = BAGS[id]
    return bag and bag.items and bag.items[slot] or nil
end

function WasRead(id)
    for _, value in ipairs(READS) do
        if value == id then return true end
    end
    return false
end

function ReadOutsideRange(first, last)
    for _, value in ipairs(READS) do
        if value < first or value > last then return true end
    end
    return false
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

function SetBag(id, size, items)
    BAGS[id] = { size = size, items = items or {} }
end

function ClearReads()
    READS = {}
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


def test_world_scan():
    lua = boot(
        "ClearReads()\n"
        'SetBag(0, 16, { [1] = Item(100, 5, 2), [3] = Item(200, 1, 4) })'
        'SetBag(1, 10, { [10] = Item(300, 20, 1) })'
        'SetBag(5, 4, { [4] = Item(400, 3, 3) })'
        "SCANNED = 0\n"
        'PB.RegisterCallback("BAGS_SCANNED", function(char) SCANNED = SCANNED + 1; LAST = char end)'
        'FireEvent("ADDON_LOADED", "PocketBank")'
        'FireEvent("PLAYER_ENTERING_WORLD")'
    )
    check(value(lua, "#TIMERS") == 1, "entering the world schedules one scan")
    check(value(lua, "TIMERS[1].delay") == 1, "the world scan waits one second")
    lua.execute("RunTimers()")

    check(value(lua, f"{CHAR} ~= nil") is True, "character saved under its GUID")
    check(value(lua, f"{TABS} ~= nil") is True, "bags saved on the character")
    check(value(lua, f"{CHAR}.bags.scanned") == 1700000000, "bags.scanned saved")
    check(value(lua, f"CountKeys({TABS})") == 6, "one tab per container")
    check(value(lua, f"{TABS}[1].id == 0 and {TABS}[6].id == 5"), "tab ids are 0..5 in order")
    check(value(lua, f"{TABS}[1].size == 16"), "backpack size saved")
    check(value(lua, f"{TABS}[2].size == 10"), "equipped bag size saved")
    check(value(lua, f"{TABS}[6].size == 4"), "reagent bag size saved")
    check(value(lua, f"{TABS}[1].items[1].id == 100 and {TABS}[1].items[1].count == 5"),
          "slot 1 item saved")
    check(value(lua, f"{TABS}[1].items[3].id == 200 and {TABS}[1].items[3].quality == 4"),
          "slot 3 quality saved")
    check(value(lua, f"{TABS}[2].items[10].id == 300 and {TABS}[2].items[10].count == 20"),
          "last slot of a bag saved")
    check(value(lua, f"{TABS}[1].items[1].link ~= nil and {TABS}[1].items[1].icon == 1100"),
          "item link and icon saved")
    check(value(lua, f"CountKeys({TABS}[1].items)") == 2, "empty slots skipped")
    check(value(lua, f"CountKeys({TABS}[3].items)") == 0, "empty bag stores no items")

    check(value(lua, "WasRead(-1)") is False, "the keyring is never read")
    check(value(lua, "ReadOutsideRange(0, 5)") is False, "only containers 0..5 are read")
    check(value(lua, "SCANNED") == 1, "BAGS_SCANNED fires once")
    check(value(lua, "LAST == PB.DB.GetChar(false)") is True, "BAGS_SCANNED receives the character")
    check(value(lua, "#CHAT") == 0, "nothing is printed to chat")

    check(value(lua, "PB.BagScan.Scan() == PocketBankDB.chars['Player-1-0001'].bags") is True,
          "Scan returns the saved bags")
    check(value(lua, "SCANNED") == 2, "a direct Scan fires BAGS_SCANNED too")
    check(value(lua, "#CHAT") == 0, "a direct Scan prints nothing")


def test_empty_slots_keep_positions():
    lua = boot(
        "ClearReads()\n"
        "SetBag(0, 4, {})\n"
        'FireEvent("ADDON_LOADED", "PocketBank")'
        'FireEvent("PLAYER_ENTERING_WORLD")'
        "RunTimers()"
    )
    check(value(lua, f"CountKeys({TABS})") == 6, "every container keeps a tab")
    for index in range(1, 7):
        check(value(lua, f"{TABS}[{index}].size") == (4 if index == 1 else 0),
              f"tab {index} keeps its size")
    check(value(lua, f"{TABS}[6].id") == 5, "an empty container keeps its id")
    check(value(lua, f"CountKeys({TABS}[1].items)") == 0, "empty bags store no items")
    check(value(lua, f"{CHAR}.bags.scanned") == 1700000000, "an empty scan still records the time")


def test_debounce():
    lua = boot(
        "ClearReads()\n"
        'SetBag(0, 4, { [1] = Item(10, 1, 1) })'
        "SCANNED = 0\n"
        'PB.RegisterCallback("BAGS_SCANNED", function() SCANNED = SCANNED + 1 end)'
        'FireEvent("ADDON_LOADED", "PocketBank")'
        'FireEvent("BAG_UPDATE_DELAYED")'
        'FireEvent("BAG_UPDATE_DELAYED")'
        'FireEvent("BAG_UPDATE_DELAYED")'
    )
    check(value(lua, "#TIMERS") == 1, "several change events schedule only one timer")
    check(value(lua, "TIMERS[1].delay") == 0.5, "the change scan is debounced by half a second")
    lua.execute("RunTimers()")
    check(value(lua, "SCANNED") == 1, "the debounced timer scans once")
    check(value(lua, f"{TABS}[1].items[1].id") == 10, "the debounced scan saves the items")

    lua.execute('FireEvent("BAG_UPDATE_DELAYED")')
    check(value(lua, "#TIMERS") == 1, "a later change schedules a new timer")


def test_rescan_replaces_contents():
    lua = boot(
        "ClearReads()\n"
        'SetBag(0, 2, { [1] = Item(10, 1, 1), [2] = Item(20, 1, 1) })'
        'FireEvent("ADDON_LOADED", "PocketBank")'
        'FireEvent("PLAYER_ENTERING_WORLD")'
        "RunTimers()"
    )
    check(value(lua, f"CountKeys({TABS}[1].items)") == 2, "the first scan stores both items")
    lua.execute(
        "BAGS[0].items[1] = nil\n"
        'SetBag(2, 12, { [12] = Item(30, 2, 3) })\n'
        'FireEvent("BAG_UPDATE_DELAYED")\n'
        "RunTimers()"
    )
    check(value(lua, f"CountKeys({TABS}[1].items)") == 1, "a rescan replaces the stored items")
    check(value(lua, f"{TABS}[1].items[2].id") == 20, "the remaining item is still stored")
    check(value(lua, f"{TABS}[3].id == 2 and {TABS}[3].size == 12"), "an empty bag slot stays in place")
    check(value(lua, f"{TABS}[3].items[12].id") == 30, "newly equipped bags are saved")


def test_logout_does_not_scan():
    lua = boot(
        "ClearReads()\n"
        'SetBag(0, 4, { [1] = Item(10, 1, 1) })'
        'FireEvent("ADDON_LOADED", "PocketBank")'
        'FireEvent("PLAYER_LOGOUT")'
    )
    check(value(lua, "#TIMERS") == 0, "logging out schedules no scan")
    check(value(lua, f"{CHAR}.bags ~= nil") is False, "logging out saves no bags")
    check(value(lua, "CountKeys(READS)") == 0, "logging out reads no container")


def main():
    check_compiles()
    test_world_scan()
    test_empty_slots_keep_positions()
    test_debounce()
    test_rescan_replaces_contents()
    test_logout_does_not_scan()
    if failures:
        print(f"\n{len(failures)} check(s) failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
