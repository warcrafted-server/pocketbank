"""Smoke test of the bank window with a permissive fake client (python + lupa).

Loads every file of PocketBank.toc in order, saves a fake bank, opens the
window and checks slots, counts, tabs and the empty state.
"""

import sys
from pathlib import Path

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parent.parent

FAKE_CLIENT = r"""
local function mock(kind)
    local o = { kind = kind, shown = true, text = nil, texture = nil, children = {} }
    -- Methods (Capitalized) are no-ops unless defined; plain fields stay nil.
    return setmetatable(o, { __index = function(t, k)
        if type(k) == "string" and k:match("^%u") then return function() end end
    end })
end

local function widget(kind)
    local o = mock(kind)
    o.Show = function(self) self.shown = true end
    o.Hide = function(self)
        self.shown = false
        if self.scripts and self.scripts.OnHide then self.scripts.OnHide(self) end
    end
    o.IsShown = function(self) return self.shown end
    o.SetShown = function(self, v) self.shown = v and true or false end
    o.SetText = function(self, v) self.text = v end
    o.GetText = function(self) return self.text end
    o.SetTexture = function(self, v) self.texture = v end
    o.SetScript = function(self, name, fn) self.scripts = self.scripts or {}; self.scripts[name] = fn end
    o.HookScript = function(self, name, fn) self.scripts = self.scripts or {}; self.scripts[name] = fn end
    o.CreateTexture = function(self) return widget("Texture") end
    o.CreateFontString = function(self) local f = widget("FontString"); ALL_FS[#ALL_FS + 1] = f; return f end
    o.GetFrameLevel = function() return 1 end
    o.SetHeight = function(self, h) self.height = h end
    o.SetupMenu = function(self, gen) self.menuGen = gen end
    o.PortraitContainer = false
    o.OverrideText = function(self, t) self.overrideText = t end
    o.SetTitle = function(self, v) self.title = v end
    return o
end

FRAMES = {}
ALL_FS = {}
BUTTONS = {}
function CreateFrame(kind, name, parent, template)
    local f = widget(kind)
    f.shown = true
    f.template = template
    if kind == "Button" then BUTTONS[#BUTTONS + 1] = f end
    if kind == "DropdownButton" then DROPDOWN = f end
    if name then _G[name] = f; FRAMES[name] = f end
    return f
end
UIParent = widget("Frame")
Minimap = widget("Frame")
Minimap.GetWidth = function() return 140 end
Minimap.GetHeight = function() return 140 end
UISpecialFrames = {}
GameTooltip = widget("GameTooltip")
function GetLocale() return "esES" end
function GetRealmName() return "CAMWOW EU5 Realm 5 PvE" end
function UnitName() return "Charman" end
function UnitGUID() return "Player-6947-011E3126" end
function UnitClass() return "Chamán", "SHAMAN" end
function UnitRace() return "Draenei", "Draenei", 11 end
function UnitSex() return 2 end
function UnitFactionGroup() return "Alliance" end
function UnitLevel() return 16 end
function GetMoney() return 16454 end
function GetCoinTextureString(v) return "coins:" .. v end
function GetCursorPosition() return 0, 0 end
C_Timer = { After = function(_, fn) fn() end }
C_AddOns = { GetAddOnMetadata = function() return "dev" end }
Enum = { BankType = { Character = 0 }, BagIndex = { CharacterBankTab_1 = 6 } }
SlashCmdList = {}
PRINTED = {}
print = function(...) PRINTED[#PRINTED + 1] = table.concat({ ... }, " ") end
time = function() return 1794871143 end
date = os.date
strtrim = function(s) return (s:gsub("^%s+", ""):gsub("%s+$", "")) end
strlower = string.lower
"""

failures = []


def check(ok, label):
    print(("PASS " if ok else "FAIL ") + label)
    if not ok:
        failures.append(label)


def toc_files():
    files = []
    for line in (ROOT / "PocketBank.toc").read_text(encoding="utf8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            files.append(line)
    return files


def boot():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(FAKE_CLIENT)
    lua.execute("PB_NS = {}")
    loader = lua.eval("function(code, name) local f, err = loadstring(code, name); if not f then error(err) end; f('PocketBankDev', PB_NS) end")
    for rel in toc_files():
        loader((ROOT / rel).read_text(encoding="utf8"), rel)
    return lua


def main():
    lua = boot()
    lua.execute("PocketBankDB = nil; FRAMES.__events = nil")
    # Fire ADDON_LOADED and PLAYER_LOGIN through every registered OnEvent.
    lua.execute("PB_NS.DB.Init(); PB_NS.DB.SaveCharMeta()")
    lua.execute("local real = GetMoney; GetMoney = function() return 0 end; "
                "PB_NS.DB.SaveCharMeta('PLAYER_LOGOUT'); GetMoney = real")
    check(lua.eval("PB_NS.DB.GetChar(false).money") == 16454, "logout does not overwrite the saved money")
    lua.execute("""
        local char = PB_NS.DB.GetChar(true)
        char.bank = { scanned = 1794871143, tabs = { { id = 6, name = 'Pestaña 1', icon = 134400, size = 48, items = {
            [1] = { id = 211785, count = 1, link = 'item:211785', icon = 237446, quality = 1 },
            [5] = { id = 2934, count = 18, link = 'item:2934', icon = 134360, quality = 1 },
            [9] = { id = 2319, count = 4, link = 'item:2319', icon = 134254, quality = 2 },
        } } } }
    """)
    lua.execute("PB_NS.ToggleWindow()")
    frame = lua.eval("PocketBankFrame")
    check(frame is not None, "window created")
    check(lua.eval("PocketBankFrame.template") == "PortraitFrameTemplate", "uses PortraitFrameTemplate")
    check(lua.eval("PocketBankFrame:IsShown()") is True, "window shown")
    check(lua.eval("PocketBankFrame.title") == "Banco de Charman", "title with the character name")
    check(lua.eval("UISpecialFrames[1]") == "PocketBankFrame", "closes with Escape")

    window = lua.eval("PB_NS.UI.BankWindow")
    check(window is not None, "BankWindow exported")
    lua.execute("""
        SLOTS = {}
        local f = PocketBankFrame
        -- slots are the 48 Buttons created with the frame as parent
    """)
    texts = lua.eval("""(function()
        local out = {}
        for _, fs in ipairs(ALL_FS) do out[#out + 1] = tostring(fs.text) end
        return table.concat(out, '|')
    end)()""")
    check("Último escaneo:" in texts, "last scan line shown")
    check("coins:16454" in texts, "money shown")

    shown_slots = lua.eval("""(function()
        local n = 0
        for _, b in ipairs(BUTTONS) do if b.shown and b.icon then n = n + 1 end end
        return n
    end)()""")
    check(shown_slots == 48, f"48 slots for the main bank (got {shown_slots})")
    check(lua.eval("PocketBankFrame.height") == 460, "standard height with 6 rows")

    lua.execute("""
        local tabs = PB_NS.DB.GetChar(true).bank.tabs
        tabs[2] = { id = 7, name = 'Pestaña 2', size = 6, items = { [2] = { id = 4238, count = 3, link = 'item:4238', icon = 133622, quality = 1 } } }
        PB_NS.UI.BankWindow:Refresh()
    """)
    shown_slots = lua.eval("""(function()
        local n = 0
        for _, b in ipairs(BUTTONS) do if b.shown and b.icon then n = n + 1 end end
        return n
    end)()""")
    check(shown_slots == 54, f"bank bag slots appended to the same grid (got {shown_slots})")
    check(lua.eval("PocketBankFrame.height") == 507, "window grows one row for the bag")
    slot50 = lua.eval("(function() local n = 0; for _, b in ipairs(BUTTONS) do if b.icon then n = n + 1; if n == 50 then return b.icon.texture end end end end)()")
    check(slot50 == 133622, "bag item lands in slot 48 + 2")

    lua.execute("PB_NS.ToggleWindow()")
    check(lua.eval("PocketBankFrame:IsShown()") is False, "toggle hides the window")

    lua.execute("PB_NS.DB.GetChar(true).bank = nil; PB_NS.ToggleWindow()")
    texts = lua.eval("""(function()
        local out = {}
        for _, fs in ipairs(ALL_FS) do out[#out + 1] = tostring(fs.text) end
        return table.concat(out, '|')
    end)()""")
    check("Aún sin datos" in texts, "empty state when the bank was never visited")

    # 0.2.0: other characters
    lua.execute("""
        PocketBankDB.chars["Player-6947-0000AAAA"] = { guid = "Player-6947-0000AAAA", name = "Zelda", fullName = "Zelda Brasaviva",
            class = "MAGE", money = 500, bank = { scanned = 1794871143, tabs = { { id = 6, size = 48, items = {
            [3] = { id = 1, count = 5, link = "item:1", icon = 111, quality = 1 } } } } } }
        PocketBankDB.chars["Player-6947-0000BBBB"] = { guid = "Player-6947-0000BBBB", name = "Abel", fullName = "Abel Sinbanco", class = "WARRIOR" }
    """)
    order = lua.eval("(function() local t = {} for _, e in ipairs(PB_NS.DB.ListChars()) do t[#t + 1] = e.key end return table.concat(t, ',') end)()")
    check(order == "Player-6947-011E3126,Player-6947-0000BBBB,Player-6947-0000AAAA", f"current character first, then by name ({order})")
    check(lua.eval("DROPDOWN ~= nil and DROPDOWN.menuGen ~= nil") is True, "native dropdown with a menu")
    lua.execute("""
        ROOT = { radios = {} }
        function ROOT:CreateRadio(text, isSelected, setSelected) self.radios[#self.radios + 1] = { text = text, isSelected = isSelected, setSelected = setSelected } end
        DROPDOWN.menuGen(DROPDOWN, ROOT)
    """)
    check(lua.eval("#ROOT.radios") == 3, "one menu entry per saved character")
    check(lua.eval("ROOT.radios[1].isSelected()") is True, "logged-in character selected by default")
    lua.execute("ROOT.radios[3].setSelected()")
    check(lua.eval("PocketBankFrame.title") == "Banco de Zelda", "selecting a character shows its bank")
    check("Zelda Brasaviva" in (lua.eval("DROPDOWN.overrideText") or ""), "dropdown shows the full two-part name")
    texts = lua.eval("""(function()
        local out = {}
        for _, fs in ipairs(ALL_FS) do out[#out + 1] = tostring(fs.text) end
        return table.concat(out, '|')
    end)()""")
    check("coins:500" in texts, "money of the selected character")
    slot3 = lua.eval("(function() local n = 0; for _, b in ipairs(BUTTONS) do if b.icon then n = n + 1; if n == 3 then return b.icon.texture end end end end)()")
    check(slot3 == 111, "items of the selected character")
    lua.execute("ROOT.radios[2].setSelected()")
    texts = lua.eval("""(function()
        local out = {}
        for _, fs in ipairs(ALL_FS) do out[#out + 1] = tostring(fs.text) end
        return table.concat(out, '|')
    end)()""")
    check("Entra con él y visita el banco" in texts, "other character without bank data")
    lua.execute("PB_NS.ToggleWindow(); PB_NS.ToggleWindow()")
    check(lua.eval("PocketBankFrame.title") == "Banco de Abel", "reopening keeps the selected character")

    # 0.3.0: bags view
    check(lua.eval("#PocketBankFrame.sideTabs") == 3, "bank, bags and equipment side tabs")
    check(lua.eval("PocketBankFrame.sideTabs[1].selected.shown") is True, "bank tab selected by default")
    lua.execute("""
        PocketBankDB.chars["Player-6947-0000AAAA"].bags = { scanned = 1794871143, tabs = {
            { id = 0, size = 20, items = { [1] = { id = 6948, count = 1, link = "item:6948", icon = 134414, quality = 1 } } },
            { id = 1, size = 6, items = {} }, { id = 2, size = 6, items = {} }, { id = 3, size = 6, items = {} },
            { id = 4, size = 12, items = { [12] = { id = 2, count = 7, link = "item:2", icon = 222, quality = 1 } } },
            { id = 5, size = 4, items = {} } } }
        ROOT.radios[3].setSelected()
        PocketBankFrame.sideTabs[2].scripts.OnClick()
    """)
    check(lua.eval("PocketBankFrame.title") == "Bolsas de Zelda", "bags tab shows the bags title")
    check(lua.eval("PocketBankFrame.sideTabs[2].selected.shown") is True, "bags tab marked as selected")
    check(lua.eval("PocketBankFrame.sideTabs[1].selected.shown") is False, "bank tab unmarked")
    shown_slots = lua.eval("""(function()
        local n = 0
        for _, b in ipairs(BUTTONS) do if b.shown and b.icon then n = n + 1 end end
        return n
    end)()""")
    check(shown_slots == 54, f"all bag slots in one grid (got {shown_slots})")
    check(lua.eval("PocketBankFrame.height") == 507, "window grows to 7 rows for 54 bag slots")
    slot1 = lua.eval("(function() local n = 0; for _, b in ipairs(BUTTONS) do if b.icon then n = n + 1; if n == 1 then return b.icon.texture end end end end)()")
    slot50 = lua.eval("(function() local n = 0; for _, b in ipairs(BUTTONS) do if b.icon then n = n + 1; if n == 50 then return b.icon.texture end end end end)()")
    check(slot1 == 134414 and slot50 == 222, "bag items in container order")
    lua.execute("ROOT.radios[2].setSelected()")
    texts = lua.eval("""(function()
        local out = {}
        for _, fs in ipairs(ALL_FS) do out[#out + 1] = tostring(fs.text) end
        return table.concat(out, '|')
    end)()""")
    check("Aún no hay datos de las bolsas" in texts, "other character without bag data")
    check(lua.eval("PocketBankFrame.title") == "Bolsas de Abel", "the view is kept when changing character")
    lua.execute("PB_NS.ToggleWindow(); PB_NS.ToggleWindow()")
    check(lua.eval("PocketBankFrame.title") == "Bolsas de Abel", "reopening keeps the bags view")
    lua.execute("PocketBankFrame.sideTabs[1].scripts.OnClick()")
    check(lua.eval("PocketBankFrame.title") == "Banco de Abel", "bank tab goes back to the bank")

    # 0.4.0: equipment view (character sheet)
    lua.execute("""
        local me = PB_NS.DB.GetChar(true)
        me.equipment = { scanned = 1794871143, slots = {
            [1] = { id = 10, link = "item:10", icon = 1001, quality = 3 },
            [16] = { id = 20, link = "item:20", icon = 1016, quality = 2 } } }
        ROOT.radios[1].setSelected()
        PocketBankFrame.sideTabs[3].scripts.OnClick()
    """)
    check(lua.eval("PocketBankFrame.title") == "Charman", "equipment view titled with the character name")
    check(lua.eval("PocketBankFrame.sideTabs[3].selected.shown") is True, "equipment tab marked as selected")
    grid_hidden = lua.eval("""(function()
        for _, part in ipairs(PocketBankFrame.gridParts) do if part.shown then return false end end
        return true
    end)()""")
    check(grid_hidden, "bank background, divider and money hidden in the equipment view")
    icons = lua.eval("""(function()
        local out = {}
        for _, b in ipairs(BUTTONS) do if b.shown and b.slotId then out[b.slotId] = b.icon.texture or 0 end end
        local n = 0 for _ in pairs(out) do n = n + 1 end
        return n .. ':' .. tostring(out[1]) .. ':' .. tostring(out[16])
    end)()""")
    check(icons == "19:1001:1016", f"19 gear slots with the saved items ({icons})")
    texts = lua.eval("""(function()
        local out = {}
        for _, fs in ipairs(ALL_FS) do if fs.text then out[#out + 1] = tostring(fs.text) end end
        return table.concat(out, '|')
    end)()""")
    check("Chamán de nivel 16" in texts, "level line with the class name")
    lua.execute("ROOT.radios[2].setSelected()")
    texts = lua.eval("""(function()
        local out = {}
        for _, fs in ipairs(ALL_FS) do if fs.text then out[#out + 1] = tostring(fs.text) end end
        return table.concat(out, '|')
    end)()""")
    check("Aún no hay datos del equipo" in texts, "other character without equipment data")
    lua.execute("PocketBankFrame.sideTabs[1].scripts.OnClick()")
    gear_hidden = lua.eval("""(function()
        for _, b in ipairs(BUTTONS) do if b.shown and b.slotId then return false end end
        return true
    end)()""")
    check(gear_hidden and lua.eval("PocketBankFrame.title") == "Banco de Abel", "back to the bank hides the gear slots")

    # 0.6.0: movable window that remembers its position
    lua.execute("""
        local f = PocketBankFrame
        f.SetPoint = function(self, ...) self.point = { ... } end
        f.GetLeft = function() return 300 end
        f.GetTop = function() return 700 end
        f.scripts.OnDragStart(f)
        f.scripts.OnDragStop(f)
    """)
    check(lua.eval("PocketBankDB.settings.window.left") == 300 and lua.eval("PocketBankDB.settings.window.top") == 700,
          "dragging saves the top-left corner")
    check(lua.eval("PocketBankFrame.point[1]") == "TOPLEFT" and lua.eval("PocketBankFrame.point[3]") == "BOTTOMLEFT"
          and lua.eval("PocketBankFrame.point[5]") == 700, "window anchored at the saved corner")
    lua.execute("SlashCmdList.POCKETBANK('reset')")
    check(lua.eval("PocketBankDB.settings.window") is None, "/pb reset forgets the position")
    check(lua.eval("PocketBankFrame.point[3]") == "TOPLEFT" and lua.eval("PocketBankFrame.point[5]") == -116,
          "/pb reset moves the window back to the default place")

    # account-wide item search
    lua.execute("""
        local me = PB_NS.DB.GetChar(true)
        me.bank = { scanned = 1794871143, tabs = { { id = 6, size = 48, items = {
            [1] = { id = 700, count = 2, link = "|cff1eff00|Hitem:700|h[Arcane Dust]|h|r", icon = 701, quality = 2 },
            [2] = { id = 701, count = 1, link = "|cffa335ee|Hitem:701|h[Rusted Blade]|h|r", icon = 702, quality = 4 },
        } } } }
        PocketBankDB.chars["Player-6947-0000AAAA"].bags = { scanned = 1794871143, tabs = { { id = 0, size = 20, items = {
            [3] = { id = 700, count = 5, link = "|cff1eff00|Hitem:700|h[Arcane Dust]|h|r", icon = 701, quality = 2 },
        } } } }
        ROOT.radios[1].setSelected()
        PocketBankFrame.sideTabs[1].scripts.OnClick()
    """)
    check(lua.eval("PocketBankFrameSearchBox ~= nil") is True, "the search box exists")
    check(lua.eval("PocketBankFrameSearchBox.template") == "SearchBoxTemplate",
          "the search box uses the client's SearchBoxTemplate")

    lua.execute("""
        local box = PocketBankFrameSearchBox
        box:SetText('dust')
        box.scripts.OnTextChanged(box)
    """)
    check(lua.eval("PocketBankFrame.title") == "Búsqueda en la cuenta", "typing shows the account search title")
    check(lua.eval("PocketBankFrame.sideTabs[1].selected.shown") is False, "no side tab is selected in search mode")
    check(lua.eval("PocketBankFrame.money.text or ''") == "", "the money is hidden in search mode")
    check("1 objetos coinciden" in (lua.eval("PocketBankFrame.scanned.text or ''")), "the match count is shown")
    found = lua.eval("""(function()
        local out = {}
        local n = 0
        for _, b in ipairs(BUTTONS) do
            if b.shown and b.icon then
                n = n + 1
                out[n] = { icon = b.icon.texture, count = b.count.text }
            end
        end
        return n .. ':' .. tostring(out[1].icon) .. ':' .. tostring(out[1].count)
    end)()""")
    check(found == "1:701:7", f"one result with the counts of every character (got {found})")

    lua.execute("""
        local box = PocketBankFrameSearchBox
        box:SetText('e')
        box.scripts.OnTextChanged(box)
    """)
    found = lua.eval("""(function()
        local out = {}
        local n = 0
        for _, b in ipairs(BUTTONS) do
            if b.shown and b.icon then n = n + 1; out[n] = tostring(b.icon.texture) end
        end
        return n .. ':' .. table.concat(out, ':')
    end)()""")
    check(found == "2:702:701", f"results sorted by quality first, then name (got {found})")
    check("2 objetos coinciden" in (lua.eval("PocketBankFrame.scanned.text or ''")), "both matches are counted")

    lua.execute("""
        local box = PocketBankFrameSearchBox
        box:SetText('zzz')
        box.scripts.OnTextChanged(box)
    """)
    text = lua.eval("PocketBankFrame.empty.text or ''")
    check("Ningún personaje" in text and "zzz" in text, "no results shows the SEARCH_NONE notice")
    check(lua.eval("PocketBankFrame.notice.shown") is True, "the notice is visible without results")
    empty_slots = lua.eval("""(function()
        local n = 0
        for _, b in ipairs(BUTTONS) do if b.shown and b.icon then n = n + 1 end end
        return n
    end)()""")
    check(empty_slots == 48, f"no results keeps the empty 8x6 grid (got {empty_slots})")

    lua.execute("PocketBankFrame.sideTabs[1].scripts.OnClick()")
    check(lua.eval("PocketBankFrameSearchBox.text or ''") == "", "clicking a side tab clears the search box")
    check(lua.eval("PocketBankFrame.title") == "Banco de Charman", "clicking a side tab leaves search mode")
    check(lua.eval("PocketBankFrame.money.text") == "coins:16454", "the money comes back after the search")
    check(lua.eval("PocketBankFrame.sideTabs[1].selected.shown") is True, "the tab is selected again")

    lua.execute("""
        local box = PocketBankFrameSearchBox
        box:SetText('dust')
        box.scripts.OnTextChanged(box)
        ROOT.radios[2].setSelected()
    """)
    check(lua.eval("PocketBankFrameSearchBox.text or ''") == "", "selecting a character clears the search box")
    check(lua.eval("PocketBankFrame.title") == "Banco de Abel", "selecting a character leaves search mode")

    lua.execute("""
        local box = PocketBankFrameSearchBox
        box:SetText('dust')
        box.scripts.OnTextChanged(box)
        PB_NS.ToggleWindow()
    """)
    check(lua.eval("PocketBankFrameSearchBox.text or ''") == "", "hiding the window clears the search box")
    lua.execute("PB_NS.ToggleWindow()")

    lua.execute("PocketBankFrame.sideTabs[3].scripts.OnClick()")
    check(lua.eval("PocketBankFrameSearchBox.shown") is False, "the search box is hidden in the equipment view")
    lua.execute("PocketBankFrame.sideTabs[1].scripts.OnClick()")
    check(lua.eval("PocketBankFrameSearchBox.shown") is True, "the search box is shown again in the bank")

    if failures:
        print(f"\n{len(failures)} check(s) failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
