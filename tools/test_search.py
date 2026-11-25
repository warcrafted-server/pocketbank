"""Simulated-client checks for the PocketBank account-wide item search."""

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
    "Modules/Search.lua",
]

ALL_LUA = sorted(
    path.relative_to(ROOT).as_posix()
    for folder in ("Core", "Locales", "Modules")
    for path in (ROOT / folder).glob("*.lua")
)

HARNESS = r"""
PB = {}
CHAT = {}
FRAMES = {}

PocketBankDB = { schemaVersion = 2, chars = {} }

function print(...)
    local parts = {}
    for i = 1, select("#", ...) do parts[i] = tostring((select(i, ...))) end
    CHAT[#CHAT + 1] = table.concat(parts, " ")
end

function GetLocale() return "enUS" end
function GetRealmName() return "Realm" end
function UnitName(unit) return "Alfa" end
function UnitGUID(unit) return "Player-1-0001" end
function UnitClass(unit) return "Warrior", "WARRIOR" end
function UnitRace(unit) return "Human", "Human", 1 end
function UnitSex(unit) return 2 end
function UnitFactionGroup(unit) return "Alliance" end
function UnitLevel(unit) return 60 end
function GetMoney() return 12345 end
function time() return 1700000000 end

Enum = {}
SlashCmdList = {}
C_AddOns = { GetAddOnMetadata = function() return "dev" end }
function strlower(s) return string.lower(s) end
function strtrim(s) return (s:gsub("^%s*(.-)%s*$", "%1")) end

function CreateFrame()
    local frame = { scripts = {} }
    function frame:RegisterEvent() end
    function frame:UnregisterEvent() end
    function frame:SetScript(name, fn) self.scripts[name] = fn end
    return frame
end

function Link(id, name)
    return "|cffa335ee|Hitem:" .. id .. ":0:0:0|h[" .. name .. "]|h|r"
end

function Item(id, count, name, quality, icon)
    return { id = id, count = count, link = Link(id, name), icon = icon or 1, quality = quality or 1 }
end

function Gear(id, name, quality, icon)
    return { id = id, link = Link(id, name), icon = icon or 1, quality = quality or 1 }
end

function AddChar(key, name, class)
    PocketBankDB.chars[key] = { guid = key, name = name, fullName = name, class = class }
end

function AddBank(key, tabs) PocketBankDB.chars[key].bank = { scanned = 1, tabs = tabs } end
function AddBags(key, tabs) PocketBankDB.chars[key].bags = { scanned = 1, tabs = tabs } end
function AddEquipment(key, slots) PocketBankDB.chars[key].equipment = { scanned = 1, slots = slots } end

function ResultNumber(text) return #(PB.Search.Find(text)) end
function Total(text) local _, total = PB.Search.Find(text) return total end

function Names(text)
    local results = PB.Search.Find(text)
    local out = {}
    for i = 1, #results do out[i] = results[i].name end
    return table.concat(out, "|")
end

function Field(text, index, key)
    local results = PB.Search.Find(text)
    return results[index] and results[index][key] or nil
end

function CountOf(text, id)
    local results = PB.Search.Find(text)
    for i = 1, #results do
        if results[i].id == id then return results[i].count end
    end
end
"""

SETUP = """
AddChar("Player-1-0001", "Alfa", "WARRIOR")
AddBank("Player-1-0001", {
    { id = 6, size = 28, items = {
        [1] = Item(100, 10, "Rusted Sword", 1, 500),
        [2] = Item(500, 1, "Golden Crown", 4, 501),
        [3] = Item(700, 2, "Silk Bandage", 1, 502),
    } },
    { id = 7, size = 28, items = { [1] = Item(100, 10, "Rusted Sword", 1, 500) } },
})
AddBags("Player-1-0001", {
    { id = 0, size = 16, items = { [1] = Item(100, 5, "Rusted Sword", 1, 500) } },
    { id = 1, size = 6, items = { [2] = Item(600, 3, "Adamantite Ore", 4, 600) } },
})
AddEquipment("Player-1-0001", { [1] = Gear(100, "Rusted Sword", 1, 500) })
AddChar("Player-4-0004", "Aaron", "HUNTER")
AddBags("Player-4-0004", { { id = 0, size = 16, items = { [1] = Item(100, 4, "Rusted Sword", 1, 500) } } })
AddChar("Player-2-0002", "Beta", "MAGE")
AddBank("Player-2-0002", { { id = 6, size = 28, items = { [1] = Item(100, 2, "Rusted Sword", 1, 500) } } })
AddChar("Player-3-0003", "Zeta", "PRIEST")
AddBags("Player-3-0003", { { id = 0, size = 16, items = { [1] = Item(900, 3, "Mystic Robe", 3, 900) } } })
AddEquipment("Player-3-0003", {
    [1] = Gear(900, "Mystic Robe", 3, 900),
    [2] = Gear(950, "Ember Wand", 2, 950),
})
"""

CAP_SETUP = """
AddChar("Player-1-0001", "Alfa", "WARRIOR")
local items = {}
for i = 1, 100 do
    items[i] = Item(1000 + i, 1, string.format("Cap Item %03d", i), 2, 1000 + i)
end
AddBank("Player-1-0001", { { id = 6, size = 100, items = items } })
"""

failures = []


def check(condition, message):
    print(("PASS " if condition else "FAIL ") + message)
    if not condition:
        failures.append(message)


def value(lua, expression):
    return lua.eval("function() return " + expression + " end")()


def boot(scenario=""):
    """Load the addon files in .toc order on a fresh fake client."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(HARNESS)
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


def check_compiles():
    lua = LuaRuntime(unpack_returned_tuples=True)
    loadstring = lua.eval("loadstring")
    for name in ALL_LUA:
        source = (ROOT / name).read_text(encoding="utf-8")
        check(loadstring(source, name) is not None, f"{name} compiles")


def test_empty_text():
    lua = boot(SETUP)
    check(value(lua, "type(PB.Search.Find(''))") == "table", "Find returns a table")
    check(value(lua, "ResultNumber('')") == 0 and value(lua, "Total('')") == 0,
          "empty text finds nothing")
    check(value(lua, "ResultNumber('   ')") == 0 and value(lua, "Total('   ')") == 0,
          "whitespace-only text finds nothing")
    check(value(lua, "ResultNumber(nil)") == 0 and value(lua, "Total(nil)") == 0,
          "a missing text finds nothing")


def test_matching():
    lua = boot(SETUP)
    check(value(lua, "Names('sword')") == "Rusted Sword", "the front of the name matches")
    check(value(lua, "Names('rusted')") == "Rusted Sword", "the front of the name matches in lower case")
    check(value(lua, "Names('RUSTED')") == "Rusted Sword", "the match is case-insensitive")
    check(value(lua, "Names('usted sw')") == "Rusted Sword", "the match can start inside the name")
    check(value(lua, "Names('  sword  ')") == "Rusted Sword", "the text is trimmed before matching")
    check(value(lua, "Total('silksword')") == 0, "the match must be contiguous")
    check(value(lua, "Total('silken')") == 0, "characters must all be present")


def test_counts():
    lua = boot(SETUP)
    check(value(lua, "CountOf('rusted', 100)") == 32,
          "bank, bags and equipment of every character are summed")
    check(value(lua, "CountOf('rusted', 100)") == 32, "the count is stable between calls")
    check(value(lua, "CountOf('ore', 600)") == 3, "bag stacks are added up")
    check(value(lua, "CountOf('golden', 500)") == 1, "a single bank item counts one")
    check(value(lua, "CountOf('ember', 950)") == 1, "an equipped item counts one")
    check(value(lua, "CountOf('mystic', 900)") == 4, "bags and equipment of the same item are added")


def test_fields():
    lua = boot(SETUP)
    check(value(lua, "Field('adamantite', 1, 'id')") == 600, "the result keeps the item id")
    check(value(lua, "Field('adamantite', 1, 'name')") == "Adamantite Ore",
          "the name comes from the link")
    check(value(lua, "Field('adamantite', 1, 'icon')") == 600, "the result keeps the icon")
    check(value(lua, "Field('adamantite', 1, 'quality')") == 4, "the result keeps the quality")
    check(value(lua, "Field('adamantite', 1, 'count')") == 3, "the result keeps the count")
    check(value(lua, "string.find(Field('adamantite', 1, 'link'), 'Adamantite Ore', 1, true) ~= nil"),
          "the result keeps the link for the tooltip")


def test_sort():
    lua = boot(SETUP)
    check(value(lua, "Names('o')") == "Adamantite Ore|Golden Crown|Mystic Robe|Rusted Sword",
          "higher quality first, then name ascending")
    check(value(lua, "Total('o')") == 4, "every match is returned when there are few")


def test_pattern_characters():
    lua = boot(SETUP)
    check(value(lua, "ResultNumber('[')") == 0, "'[' is taken literally")
    check(value(lua, "ResultNumber('%')") == 0, "'%' is taken literally")
    check(value(lua, "ResultNumber('%d')") == 0, "a pattern class is taken literally")
    check(value(lua, "ResultNumber('(')") == 0, "'(' is taken literally")
    check(value(lua, "ResultNumber('.')") == 0, "'.' is taken literally")


def test_cap():
    lua = boot(CAP_SETUP)
    check(value(lua, "Total('cap item')") == 100, "the total counts every match")
    check(value(lua, "ResultNumber('cap item')") == 80, "at most ten rows of eight results")
    names = value(lua, "Names('cap item')").split("|")
    check(names[0] == "Cap Item 001", "the first sorted match comes first")
    check(names[-1] == "Cap Item 080", "the cap keeps the first eighty matches")


def test_no_saved_data():
    lua = boot()
    check(value(lua, "Total('sword')") == 0, "a store without characters finds nothing")
    lua.execute("PocketBankDB = nil")
    check(value(lua, "Total('sword')") == 0, "a missing saved-data store finds nothing")


def main():
    check_compiles()
    test_empty_text()
    test_matching()
    test_counts()
    test_fields()
    test_sort()
    test_pattern_characters()
    test_cap()
    test_no_saved_data()
    if failures:
        print(f"\n{len(failures)} check(s) failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
