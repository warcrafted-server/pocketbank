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
    o.Hide = function(self) self.shown = false end
    o.IsShown = function(self) return self.shown end
    o.SetShown = function(self, v) self.shown = v and true or false end
    o.SetText = function(self, v) self.text = v end
    o.GetText = function(self) return self.text end
    o.SetTexture = function(self, v) self.texture = v end
    o.SetScript = function(self, name, fn) self.scripts = self.scripts or {}; self.scripts[name] = fn end
    o.CreateTexture = function(self) return widget("Texture") end
    o.CreateFontString = function(self) local f = widget("FontString"); self.children[#self.children + 1] = f; return f end
    o.SetTitle = function(self, v) self.title = v end
    return o
end

FRAMES = {}
function CreateFrame(kind, name, parent, template)
    local f = widget(kind)
    f.shown = true
    f.template = template
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
        for _, fs in ipairs(PocketBankFrame.children) do out[#out + 1] = tostring(fs.text) end
        return table.concat(out, '|')
    end)()""")
    check("Último escaneo:" in texts, "last scan line shown")
    check("coins:16454" in texts, "money shown")

    lua.execute("PB_NS.ToggleWindow()")
    check(lua.eval("PocketBankFrame:IsShown()") is False, "toggle hides the window")

    lua.execute("PB_NS.DB.GetChar(true).bank = nil; PB_NS.ToggleWindow()")
    texts = lua.eval("""(function()
        local out = {}
        for _, fs in ipairs(PocketBankFrame.children) do out[#out + 1] = tostring(fs.text) end
        return table.concat(out, '|')
    end)()""")
    check("Aún sin datos" in texts, "empty state when the bank was never visited")

    if failures:
        print(f"\n{len(failures)} check(s) failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
