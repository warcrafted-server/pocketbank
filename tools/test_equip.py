"""Simulated-client checks for the PocketBank equipment scanner."""

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
    "Modules/EquipScan.lua",
]

ALL_LUA = sorted(
    path.relative_to(ROOT).as_posix()
    for folder in ("Core", "Locales", "Modules")
    for path in (ROOT / folder).glob("*.lua")
)

CHAR = 'PocketBankDB.chars["Player-1-0001"]'
SLOTS = f"{CHAR}.equipment.slots"

HARNESS = r"""
PB = {}
CHAT = {}
TIMERS = {}
FRAMES = {}
GEAR = {}
BROKEN = {}
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
function UnitRace(unit) return "Human", "Human", 1 end
function UnitSex(unit) return 2 end
function UnitFactionGroup(unit) return "Alliance" end
function UnitLevel(unit) return 60 end
function GetMoney() return 12345 end
function time() return 1700000000 end

function Fail(slot)
    if BROKEN[slot] then error("inventory slot " .. slot .. " unavailable") end
end

function GetInventoryItemLink(unit, slot)
    READS[#READS + 1] = slot
    Fail(slot)
    local item = GEAR[slot]
    return item and item.link or nil
end

function GetInventoryItemID(unit, slot)
    Fail(slot)
    local item = GEAR[slot]
    if not item or item.noID then return nil end
    return item.id
end

function GetInventoryItemTexture(unit, slot)
    Fail(slot)
    local item = GEAR[slot]
    return item and item.icon or nil
end

function GetInventoryItemQuality(unit, slot)
    Fail(slot)
    local item = GEAR[slot]
    return item and item.quality or nil
end

function WasRead(slot)
    for _, value in ipairs(READS) do
        if value == slot then return true end
    end
    return false
end

function ReadOutsideRange(first, last)
    for _, value in ipairs(READS) do
        if value < first or value > last then return true end
    end
    return false
end

function ClearReads()
    READS = {}
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

function Gear(slot, id, quality)
    GEAR[slot] = {
        id = id,
        link = "|cffa335ee|Hitem:" .. id .. ":0:0:0:0:0:0:0|h[Gear " .. id .. "]|h|r",
        icon = 2000 + id,
        quality = quality or 4,
    }
end

function GearWithoutID(slot, id, quality)
    Gear(slot, id, quality)
    GEAR[slot].noID = true
end

function BrokenSlot(slot)
    BROKEN[slot] = true
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
        "Gear(1, 100, 4)\n"
        "Gear(15, 200, 2)\n"
        "Gear(16, 300, 3)\n"
        "SCANNED = 0\n"
        'PB.RegisterCallback("EQUIPMENT_SCANNED", function(char) SCANNED = SCANNED + 1; LAST = char end)'
        'FireEvent("ADDON_LOADED", "PocketBank")'
        'FireEvent("PLAYER_ENTERING_WORLD")'
    )
    check(value(lua, "#TIMERS") == 1, "entering the world schedules one scan")
    check(value(lua, "TIMERS[1].delay") == 1, "the world scan waits one second")
    lua.execute("RunTimers()")

    check(value(lua, f"{CHAR} ~= nil") is True, "character saved under its GUID")
    check(value(lua, f"{SLOTS} ~= nil") is True, "equipment saved on the character")
    check(value(lua, f"{CHAR}.equipment.scanned") == 1700000000, "equipment.scanned saved")
    check(value(lua, f"CountKeys({SLOTS})") == 3, "only occupied slots are stored")
    check(value(lua, f"{SLOTS}[1].id == 100 and {SLOTS}[1].quality == 4"), "head slot id and quality saved")
    check(value(lua, f"{SLOTS}[1].link ~= nil and {SLOTS}[1].icon == 2100"),
          "slot link and icon saved")
    check(value(lua, f"{SLOTS}[15].id == 200"), "back slot saved")
    check(value(lua, f"{SLOTS}[16].id == 300 and {SLOTS}[16].quality == 3"),
          "main hand slot saved")
    check(value(lua, f"{SLOTS}[2] == nil and {SLOTS}[19] == nil"), "empty slots are not stored")

    check(value(lua, "ReadOutsideRange(0, 19)") is False, "only slots 0..19 are read")
    check(value(lua, "WasRead(0) and WasRead(19)") is True, "the range includes slot 0 and 19")
    check(value(lua, "SCANNED") == 1, "EQUIPMENT_SCANNED fires once")
    check(value(lua, "LAST == PB.DB.GetChar(false)") is True, "EQUIPMENT_SCANNED receives the character")
    check(value(lua, "#CHAT") == 0, "nothing is printed to chat")

    check(value(lua, "PB.EquipScan.Scan() == PocketBankDB.chars['Player-1-0001'].equipment") is True,
          "Scan returns the saved equipment")
    check(value(lua, "SCANNED") == 2, "a direct Scan fires EQUIPMENT_SCANNED too")
    check(value(lua, "#CHAT") == 0, "a direct Scan prints nothing")


def test_broken_slots_are_skipped():
    lua = boot(
        "ClearReads()\n"
        "Gear(1, 100, 4)\n"
        "BrokenSlot(5)\n"
        "BrokenSlot(9)\n"
        'FireEvent("ADDON_LOADED", "PocketBank")'
        'FireEvent("PLAYER_ENTERING_WORLD")'
        "RunTimers()"
    )
    check(value(lua, f"CountKeys({SLOTS})") == 1, "a failing slot is not stored")
    check(value(lua, f"{SLOTS}[5] == nil and {SLOTS}[9] == nil"), "failing slots are skipped")
    check(value(lua, f"{SLOTS}[1].id") == 100, "the scan continues after a failing slot")
    check(value(lua, f"{CHAR}.equipment.scanned") == 1700000000, "a scan with errors still records the time")
    check(value(lua, "#CHAT") == 0, "a failing slot prints nothing")


def test_id_from_link():
    lua = boot(
        "ClearReads()\n"
        "GearWithoutID(7, 400, 3)\n"
        'FireEvent("ADDON_LOADED", "PocketBank")'
        'FireEvent("PLAYER_ENTERING_WORLD")'
        "RunTimers()"
    )
    check(value(lua, f"{SLOTS}[7].id") == 400, "the id is parsed from the link")
    check(value(lua, f"{SLOTS}[7].link ~= nil") is True, "the link is kept")
    check(value(lua, f"CountKeys({SLOTS})") == 1, "a slot without API id is still stored")


def test_debounce():
    lua = boot(
        "ClearReads()\n"
        "Gear(1, 10, 1)\n"
        "SCANNED = 0\n"
        'PB.RegisterCallback("EQUIPMENT_SCANNED", function() SCANNED = SCANNED + 1 end)'
        'FireEvent("ADDON_LOADED", "PocketBank")'
        'FireEvent("PLAYER_EQUIPMENT_CHANGED")'
        'FireEvent("PLAYER_EQUIPMENT_CHANGED")'
        'FireEvent("PLAYER_EQUIPMENT_CHANGED")'
    )
    check(value(lua, "#TIMERS") == 1, "several equipment changes schedule only one timer")
    check(value(lua, "TIMERS[1].delay") == 0.5, "the change scan is debounced by half a second")
    lua.execute("RunTimers()")
    check(value(lua, "SCANNED") == 1, "the debounced timer scans once")
    check(value(lua, f"{SLOTS}[1].id") == 10, "the debounced scan saves the slots")

    lua.execute('FireEvent("PLAYER_EQUIPMENT_CHANGED")')
    check(value(lua, "#TIMERS") == 1, "a later change schedules a new timer")


def test_rescan_replaces_slots():
    lua = boot(
        "ClearReads()\n"
        "Gear(1, 10, 1)\n"
        "Gear(2, 20, 1)\n"
        'FireEvent("ADDON_LOADED", "PocketBank")'
        'FireEvent("PLAYER_ENTERING_WORLD")'
        "RunTimers()"
    )
    check(value(lua, f"CountKeys({SLOTS})") == 2, "the first scan stores both slots")
    lua.execute(
        "GEAR[1] = nil\n"
        "Gear(3, 30, 2)\n"
        'FireEvent("PLAYER_EQUIPMENT_CHANGED")\n'
        "RunTimers()"
    )
    check(value(lua, f"CountKeys({SLOTS})") == 2, "a rescan replaces the stored slots")
    check(value(lua, f"{SLOTS}[1] == nil"), "an unequipped item is dropped")
    check(value(lua, f"{SLOTS}[2].id") == 20, "the remaining slot is still stored")
    check(value(lua, f"{SLOTS}[3].id") == 30, "the newly equipped item is saved")


def test_logout_does_not_scan():
    lua = boot(
        "ClearReads()\n"
        "Gear(1, 10, 1)\n"
        'FireEvent("ADDON_LOADED", "PocketBank")'
        'FireEvent("PLAYER_LOGOUT")'
    )
    check(value(lua, "#TIMERS") == 0, "logging out schedules no scan")
    check(value(lua, f"{CHAR}.equipment ~= nil") is False, "logging out saves no equipment")
    check(value(lua, "CountKeys(READS)") == 0, "logging out reads no slot")


def main():
    check_compiles()
    test_world_scan()
    test_broken_slots_are_skipped()
    test_id_from_link()
    test_debounce()
    test_rescan_replaces_slots()
    test_logout_does_not_scan()
    if failures:
        print(f"\n{len(failures)} check(s) failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
