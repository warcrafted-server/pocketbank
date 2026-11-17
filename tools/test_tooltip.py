"""Simulated-client checks for the PocketBank item tooltip."""

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
    "Modules/Tooltip.lua",
]

ALL_LUA = sorted(
    path.relative_to(ROOT).as_posix()
    for folder in ("Core", "Locales", "Modules")
    for path in (ROOT / folder).glob("*.lua")
)

SETUP = """
AddChar("Player-1-0001", "Alfa", "WARRIOR")
AddBank("Player-1-0001", {
    { id = 6, size = 28, items = { [1] = Item(100, 10), [2] = Item(500, 1) } },
    { id = 7, size = 28, items = { [1] = Item(100, 10) } },
})
AddBags("Player-1-0001", { { id = 0, size = 16, items = { [1] = Item(100, 5) } } })
AddEquipment("Player-1-0001", { [1] = Gear(100) })
AddChar("Player-4-0004", "Aaron", "HUNTER")
AddBags("Player-4-0004", { { id = 0, size = 16, items = { [1] = Item(100, 4) } } })
AddChar("Player-2-0002", "Beta", "MAGE")
AddBank("Player-2-0002", { { id = 6, size = 28, items = { [1] = Item(100, 2) } } })
AddChar("Player-3-0003", "Zeta", "PRIEST")
AddBags("Player-3-0003", { { id = 0, size = 16, items = { [1] = Item(900, 3) } } })
"""

CACHE_SETUP = """
AddChar("Player-1-0001", "Alfa", "WARRIOR")
AddBags("Player-1-0001", { { id = 0, size = 16, items = { [1] = Item(100, 1) } } })
"""

HARNESS = r"""
PB = {}
CHAT = {}
FRAMES = {}
LOCALE = "enUS"

PocketBankDB = { schemaVersion = 2, chars = {} }

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

function GetLocale() return LOCALE end
function SetLocale(value) LOCALE = value end
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
RAID_CLASS_COLORS = {
    WARRIOR = { colorStr = "ffc79c6e" },
    MAGE = { colorStr = "ff3fc7eb" },
}

function CreateFrame(kind)
    local frame = { events = {}, scripts = {} }
    function frame:RegisterEvent(event) self.events[event] = true end
    function frame:UnregisterEvent(event) self.events[event] = nil end
    function frame:SetScript(name, fn) self.scripts[name] = fn end
    FRAMES[#FRAMES + 1] = frame
    return frame
end

SlashCmdList = {}
C_AddOns = { GetAddOnMetadata = function(_, field) return field == "Version" and "dev" or nil end }
function strlower(s) return string.lower(s) end
function strtrim(s) return (s:gsub("^%s*(.-)%s*$", "%1")) end

function AddChar(key, fullName, class)
    PocketBankDB.chars[key] = { guid = key, fullName = fullName, name = fullName, class = class }
end

function AddBank(key, tabs) PocketBankDB.chars[key].bank = { scanned = 1, tabs = tabs } end
function AddBags(key, tabs) PocketBankDB.chars[key].bags = { scanned = 1, tabs = tabs } end
function AddEquipment(key, slots) PocketBankDB.chars[key].equipment = { scanned = 1, slots = slots } end

function Item(id, count)
    return { id = id, count = count or 1, link = "item:" .. id, icon = 1, quality = 1 }
end

function Gear(id)
    return { id = id, link = "item:" .. id, icon = 1, quality = 4 }
end

function NewTooltip(name)
    local tooltip = { name = name, lines = {}, shown = 0 }
    function tooltip:GetName() return self.name end
    function tooltip:GetItem()
        local id = self.itemID
        if not id then return nil end
        return "Item " .. id, "|cffa335ee|Hitem:" .. id .. ":0:0:0|h[Item " .. id .. "]|h|r"
    end
    function tooltip:AddDoubleLine(left, right, lr, lg, lb, rr, rg, rb)
        self.lines[#self.lines + 1] = {
            left = left, right = right,
            lr = lr, lg = lg, lb = lb, rr = rr, rg = rg, rb = rb,
        }
    end
    function tooltip:Show() self.shown = self.shown + 1 end
    function tooltip:HookScript(event, fn)
        self.scripts = self.scripts or {}
        self.scripts[event] = fn
    end
    return tooltip
end

GameTooltip = NewTooltip("GameTooltip")
ItemRefTooltip = NewTooltip("ItemRefTooltip")
ShoppingTooltip1 = NewTooltip("ShoppingTooltip1")

function EnableDataProcessor()
    TooltipDataProcessor = { callbacks = {} }
    function TooltipDataProcessor.AddTooltipPostCall(kind, fn)
        TooltipDataProcessor.callbacks[#TooltipDataProcessor.callbacks + 1] = { kind = kind, fn = fn }
    end
    Enum.TooltipDataType = { Item = 7 }
end

function ShowItem(tooltip, id)
    tooltip.itemID = id
    if TooltipDataProcessor then
        for _, entry in ipairs(TooltipDataProcessor.callbacks) do entry.fn(tooltip, { id = id }) end
    else
        local script = tooltip.scripts and tooltip.scripts.OnTooltipSetItem
        if script then script(tooltip) end
    end
end

function ClearTooltip(tooltip)
    tooltip.lines = {}
    tooltip.shown = 0
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


def boot(scenario="", pre=""):
    """Load the addon files in .toc order on a fresh fake client."""
    lua = new_state()
    if pre:
        lua.execute(pre)
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


def keys_of(lua, item_id):
    return lua.eval(
        "(function() local t = {} for _, e in ipairs(PB.Tooltip.GetCounts(%d)) do"
        " t[#t + 1] = e.key end return table.concat(t, ',') end)()" % item_id
    )


def check_compiles():
    lua = new_state()
    loadstring = lua.eval("loadstring")
    for name in ALL_LUA:
        source = (ROOT / name).read_text(encoding="utf-8")
        check(loadstring(source, name) is not None, f"{name} compiles")


def test_counts():
    lua = boot(SETUP)
    check(value(lua, "type(PB.Tooltip.GetCounts(100))") == "table", "GetCounts returns a table")
    check(value(lua, "#PB.Tooltip.GetCounts(100)") == 3, "three characters hold the item")
    check(keys_of(lua, 100) == "Player-1-0001,Player-4-0004,Player-2-0002",
          "characters follow the ListChars order, logged-in one first")
    check(value(lua, "PB.Tooltip.GetCounts(100)[1].char.fullName") == "Alfa", "the entry keeps the character")
    check(value(lua, "PB.Tooltip.GetCounts(100)[1].bank") == 20, "bank stacks of several tabs are summed")
    check(value(lua, "PB.Tooltip.GetCounts(100)[1].bags") == 5, "bag stacks are summed")
    check(value(lua, "PB.Tooltip.GetCounts(100)[1].equipped") == 1, "the equipped item counts one")
    check(value(lua, "PB.Tooltip.GetCounts(100)[1].total") == 26, "the total adds bank, bags and equipment")
    check(value(lua, "PB.Tooltip.GetCounts(100)[2].bank == 0 and PB.Tooltip.GetCounts(100)[2].bags == 4"),
          "a character without a bank is counted from its bags")
    check(value(lua, "PB.Tooltip.GetCounts(100)[3].bank") == 2, "the bank of another character is counted")
    check(value(lua, "PB.Tooltip.GetCounts(900)[1].bags") == 3, "an item only in bags is counted")
    check(value(lua, "PB.Tooltip.GetCounts(4242) ~= nil and CountKeys(PB.Tooltip.GetCounts(4242))") == 0,
          "an item nobody holds returns the empty table")
    check(value(lua, "CountKeys(PB.Tooltip.GetCounts(nil))") == 0, "a missing item id returns the empty table")
    check(value(lua, "PB.Tooltip.GetCounts(100) == PB.Tooltip.GetCounts(100)") is True, "the index is cached")


def test_cache_rebuild():
    lua = boot(CACHE_SETUP)
    check(value(lua, "PB.Tooltip.GetCounts(100)[1].bags") == 1, "the first read builds the index")
    lua.execute("AddBags('Player-1-0001', { { id = 0, size = 16, items = { [1] = Item(100, 4) } } })")
    check(value(lua, "PB.Tooltip.GetCounts(100)[1].bags") == 1, "saved data alone does not rebuild the index")
    lua.execute("PB.FireCallback('BAGS_SCANNED', PB.DB.GetChar(false))")
    check(value(lua, "PB.Tooltip.GetCounts(100)[1].bags") == 4, "BAGS_SCANNED rebuilds the index")
    check(value(lua, "PB.Tooltip.GetCounts(100)[1].total") == 4, "the rebuilt index has the new total")

    lua.execute("AddBank('Player-1-0001', { { id = 6, size = 28, items = { [1] = Item(100, 6) } } })")
    check(value(lua, "PB.Tooltip.GetCounts(100)[1].bank") == 0, "the index stays cached after a bank change")
    lua.execute("PB.FireCallback('BANK_SCANNED', PB.DB.GetChar(false))")
    check(value(lua, "PB.Tooltip.GetCounts(100)[1].total") == 10, "BANK_SCANNED rebuilds the index")

    lua.execute("AddEquipment('Player-1-0001', { [1] = Gear(100) })")
    lua.execute("PB.FireCallback('EQUIPMENT_SCANNED', PB.DB.GetChar(false))")
    check(value(lua, "PB.Tooltip.GetCounts(100)[1].equipped") == 1, "EQUIPMENT_SCANNED rebuilds the index")


def test_data_processor_lines():
    lua = boot(SETUP, pre="EnableDataProcessor()")
    check(value(lua, "#TooltipDataProcessor.callbacks") == 1,
          "the data processor is used when the client has it")
    check(value(lua, "TooltipDataProcessor.callbacks[1].kind") == 7, "the post call listens to item tooltips")
    check(value(lua, "GameTooltip.scripts == nil") is True,
          "no tooltip script is hooked when the data processor exists")

    lua.execute("ShowItem(GameTooltip, 100)")
    check(value(lua, "#GameTooltip.lines") == 4, "one line per character plus the total")
    check(value(lua, "GameTooltip.lines[1].left") == "|cffc79c6eAlfa|r",
          "the left side is the class-colored name")
    check(value(lua, "GameTooltip.lines[1].right") == "26 (Bank: 20, Bags: 5, Equipped: 1)",
          "the right side is the total with the non-zero parts")
    check(value(lua, "GameTooltip.lines[1].rr == 1 and GameTooltip.lines[1].rg == 1"
                     " and GameTooltip.lines[1].rb == 1") is True, "the right side is white")
    check(value(lua, "GameTooltip.lines[2].left") == "Aaron", "a class without a color is left uncolored")
    check(value(lua, "GameTooltip.lines[3].left") == "|cff3fc7ebBeta|r",
          "each character keeps its own class color")
    check(value(lua, "GameTooltip.lines[3].right") == "2 (Bank: 2)", "only the non-zero parts are listed")
    check(value(lua, "GameTooltip.lines[4].left") == "Total", "the total line comes last")
    check(value(lua, "GameTooltip.lines[4].right") == "32", "the total line sums every character")
    check(value(lua, "GameTooltip.lines[4].lr == 1 and GameTooltip.lines[4].lg == 0.82"
                     " and GameTooltip.lines[4].lb == 0") is True, "the total label is gold")
    check(value(lua, "GameTooltip.shown") == 1, "the tooltip is shown after adding the lines")

    lua.execute("ClearTooltip(GameTooltip)\nShowItem(GameTooltip, 900)")
    check(value(lua, "#GameTooltip.lines") == 1, "a single holder gets no total line")
    check(value(lua, "GameTooltip.lines[1].left") == "Zeta", "the character is named without a class color")
    check(value(lua, "GameTooltip.lines[1].right") == "3 (Bags: 3)", "the parts of a single holder are listed")

    lua.execute("ClearTooltip(GameTooltip)\nShowItem(GameTooltip, 4242)")
    check(value(lua, "#GameTooltip.lines") == 0, "an item nobody holds adds no lines")
    check(value(lua, "GameTooltip.shown") == 0, "an item nobody holds does not show the tooltip")

    lua.execute("ShowItem(ShoppingTooltip1, 100)")
    check(value(lua, "#ShoppingTooltip1.lines") == 0, "comparison tooltips get no lines")
    check(value(lua, "ShoppingTooltip1.shown") == 0, "comparison tooltips are not shown by the addon")


def test_script_path():
    lua = boot(SETUP)
    check(value(lua, "TooltipDataProcessor == nil") is True, "this client has no data processor")
    check(value(lua, "GameTooltip.scripts.OnTooltipSetItem ~= nil") is True, "GameTooltip is hooked")
    check(value(lua, "ItemRefTooltip.scripts.OnTooltipSetItem ~= nil") is True, "ItemRefTooltip is hooked")

    lua.execute("ShowItem(GameTooltip, 100)")
    check(value(lua, "#GameTooltip.lines") == 4, "the script path adds the same lines")
    check(value(lua, "GameTooltip.lines[1].left") == "|cffc79c6eAlfa|r", "the character name keeps its color")
    check(value(lua, "GameTooltip.lines[4].left") == "Total", "the script path adds the total line")
    check(value(lua, "GameTooltip.shown") == 1, "the script path shows the tooltip")

    lua.execute("ShowItem(ItemRefTooltip, 100)")
    check(value(lua, "#ItemRefTooltip.lines") == 4, "the item reference tooltip is filled too")

    lua.execute("ClearTooltip(GameTooltip)\nShowItem(GameTooltip, nil)")
    check(value(lua, "#GameTooltip.lines") == 0, "a tooltip without an item link gets no lines")
    check(value(lua, "GameTooltip.shown") == 0, "a tooltip without an item link is not shown")


def test_spanish_labels():
    lua = boot(SETUP, pre="SetLocale('esES')")
    lua.execute("ShowItem(GameTooltip, 100)")
    check(value(lua, "GameTooltip.lines[1].right") == "26 (Banco: 20, Bolsas: 5, Equipado: 1)",
          "Spanish bank, bags and equipment labels")
    check(value(lua, "GameTooltip.lines[4].left") == "Total", "the Spanish total label")


def main():
    check_compiles()
    test_counts()
    test_cache_rebuild()
    test_data_processor_lines()
    test_script_path()
    test_spanish_labels()
    if failures:
        print(f"\n{len(failures)} check(s) failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
