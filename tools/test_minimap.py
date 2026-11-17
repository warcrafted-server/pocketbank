"""Simulated-client checks for the PocketBank minimap button."""

import math
import sys
from pathlib import Path

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parent.parent

RUNTIME_FILES = [
    "Locales/Locale.lua",
    "Locales/enUS.lua",
    "Locales/esES.lua",
    "Core/Init.lua",
    "UI/MinimapButton.lua",
]

ALL_LUA = sorted(
    path.relative_to(ROOT).as_posix()
    for folder in ("Core", "Locales", "Modules", "UI")
    for path in (ROOT / folder).glob("*.lua")
)

ICON = "Interface\\AddOns\\{}\\Media\\logo"

HARNESS = r"""
PB = {}
CHAT = {}
FRAMES = {}
BANKWINDOW_TOGGLES = 0
OPTIONS_OPENED = 0
PocketBankDB = { schemaVersion = 1, chars = {} }

MINIMAP_WIDTH, MINIMAP_HEIGHT = 150, 150
MINIMAP_SHAPE = "ROUND"
MINIMAP_CENTER = { 0, 0 }
CURSOR = { 0, 0 }

function print(...)
    local parts = {}
    for i = 1, select("#", ...) do parts[i] = tostring((select(i, ...))) end
    CHAT[#CHAT + 1] = table.concat(parts, " ")
end

function GetLocale() return "enUS" end
function GetCursorPosition() return CURSOR[1], CURSOR[2] end

Minimap = {}
function Minimap:GetWidth() return MINIMAP_WIDTH end
function Minimap:GetHeight() return MINIMAP_HEIGHT end
function Minimap:GetMinimapShape() return MINIMAP_SHAPE end
function Minimap:GetCenter() return MINIMAP_CENTER[1], MINIMAP_CENTER[2] end
function Minimap:GetEffectiveScale() return 1 end

GameTooltip = { lines = {}, shown = false }
function GameTooltip:SetOwner(owner, anchor) self.owner, self.anchor = owner, anchor end
function GameTooltip:AddLine(text, r, g, b, wrap) self.lines[#self.lines + 1] = text end
function GameTooltip:Show() self.shown = true end
function GameTooltip:Hide() self.shown = false end

BUTTON = nil

function CreateFrame(kind, name, parent)
    local frame = { kind = kind, name = name, parent = parent, scripts = {}, textures = {} }
    function frame:SetSize(width, height) self.width, self.height = width, height end
    function frame:GetWidth() return self.width or 0 end
    function frame:GetHeight() return self.height or 0 end
    function frame:SetFrameStrata(value) self.strata = value end
    function frame:SetFrameLevel(value) self.level = value end
    function frame:RegisterForClicks(...) self.clicks = { ... } end
    function frame:RegisterForDrag(...) self.drags = { ... } end
    function frame:CreateTexture(textureName, layer)
        local texture = { layer = layer }
        function texture:SetTexture(file) self.file = file end
        function texture:SetSize(width, height) self.width, self.height = width, height end
        function texture:SetPoint(...) self.point = { ... } end
        function texture:SetBlendMode(mode) self.blend = mode end
        frame.textures[#frame.textures + 1] = texture
        return texture
    end
    function frame:SetScript(event, fn) self.scripts[event] = fn end
    function frame:GetScript(event) return self.scripts[event] end
    function frame:ClearAllPoints() self.point = nil end
    function frame:SetPoint(...) self.point = { ... } end
    function frame:Hide() self.shown = false end
    function frame:Show() self.shown = true end
    function frame:IsShown() return self.shown ~= false end
    function frame:RegisterEvent(event)
        self.events = self.events or {}
        self.events[event] = true
    end
    function frame:UnregisterEvent(event)
        if self.events then self.events[event] = nil end
    end
    if kind == "Button" and name then BUTTON = frame end
    FRAMES[#FRAMES + 1] = frame
    return frame
end

function FireEvent(event, ...)
    for _, frame in ipairs(FRAMES) do
        if frame.events and frame.events[event] and frame.scripts.OnEvent then
            frame.scripts.OnEvent(frame, event, ...)
        end
    end
end

SlashCmdList = {}
C_AddOns = { GetAddOnMetadata = function(_, field) return field == "Version" and "dev" or nil end }
function strlower(s) return string.lower(s) end
function strtrim(s) return (s:gsub("^%s*(.-)%s*$", "%1")) end

function TextureFiles()
    local files = {}
    for index, texture in ipairs(BUTTON.textures) do files[index] = texture.file end
    return table.concat(files, ", ")
end

function Distance()
    local point = BUTTON.point
    return math.sqrt(point[4] * point[4] + point[5] * point[5])
end
"""

failures = []


def check(condition, message):
    print(("PASS " if condition else "FAIL ") + message)
    if not condition:
        failures.append(message)


def boot(addon="PocketBank"):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(HARNESS)
    pb = lua.globals().PB
    for name in RUNTIME_FILES:
        source = (ROOT / name).read_text(encoding="utf-8")
        chunk = lua.eval("loadstring")(source, name)
        if chunk is None:
            raise SystemExit(f"cannot load {name}")
        chunk(addon, pb)
    lua.execute('FireEvent("PLAYER_LOGIN")')
    return lua


def value(lua, expression):
    return lua.eval("function() return " + expression + " end")()


def check_compiles():
    lua = LuaRuntime(unpack_returned_tuples=True)
    loadstring = lua.eval("loadstring")
    for name in ALL_LUA:
        source = (ROOT / name).read_text(encoding="utf-8")
        check(loadstring(source, name) is not None, f"{name} compiles")


def test_button_creation():
    lua = boot()
    check(value(lua, "BUTTON ~= nil") is True, "button is created on PLAYER_LOGIN")
    check(value(lua, 'BUTTON.name == "PocketBankMinimapButton"'), "button is named after the addon")
    check(value(lua, "BUTTON.parent == Minimap"), "button is parented to the minimap")
    check(value(lua, "BUTTON.width == 31 and BUTTON.height == 31"), "button is 31x31")
    check(value(lua, 'BUTTON.strata == "MEDIUM" and BUTTON.level == 8'), "button uses the minimap strata")
    check(value(lua, 'BUTTON.clicks[1] == "LeftButtonUp"'), "button registers left clicks")
    check(value(lua, 'BUTTON.clicks[2] == "RightButtonUp"'), "button registers right clicks")
    check(value(lua, 'BUTTON.drags[1] == "LeftButton"'), "button registers left-button dragging")

    check(value(lua, "#BUTTON.textures") == 4, "button has background, icon, border and highlight")
    check(value(lua, "BUTTON.textures[1].file") == "Interface\\Minimap\\UI-Minimap-Background",
          "background texture is the minimap background")
    check(value(lua, "BUTTON.textures[2].file") == ICON.format("PocketBank"),
          "icon uses the addon logo")
    check(value(lua, "BUTTON.textures[3].file") == "Interface\\Minimap\\MiniMap-TrackingBorder",
          "border texture is the tracking border")
    check(value(lua, "BUTTON.textures[4].file") == "Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight",
          "highlight texture is the zoom-button highlight")

    check(value(lua, "PocketBankDB.settings.minimap.angle") == 225, "default angle is 225")
    check(value(lua, "PocketBankDB.settings.minimap.hide") is False, "button is visible by default")


def test_icon_follows_addon_folder():
    lua = boot("PocketBankDev")
    check(value(lua, "BUTTON.textures[2].file") == ICON.format("PocketBankDev"),
          "icon path follows the ADDON folder name")


def test_angle_math():
    lua = boot()
    radius = 150 / 2 + 5
    for angle in (0, 45, 90, 180, 225, 300):
        lua.execute(f"PocketBankDB.settings.minimap.angle = {angle}; PB.UI.MinimapButton:Refresh()")
        x, y = value(lua, "BUTTON.point[4]"), value(lua, "BUTTON.point[5]")
        expected_x = math.cos(math.radians(angle)) * radius
        expected_y = math.sin(math.radians(angle)) * radius
        check(abs(x - expected_x) < 1e-6 and abs(y - expected_y) < 1e-6,
              f"angle {angle} places the button at ({expected_x:.2f}, {expected_y:.2f})")
        check(abs(math.hypot(x, y) - radius) < 1e-6,
              f"angle {angle} keeps the button on the minimap circle")
    check(value(lua, "BUTTON.point[1]") == "CENTER" and value(lua, "BUTTON.point[3]") == "CENTER",
          "button is anchored to the minimap center")

    lua.execute('MINIMAP_SHAPE = "SQUARE"; MINIMAP_WIDTH, MINIMAP_HEIGHT = 120, 140')
    lua.execute("PB.UI.MinimapButton:Refresh()")
    check(abs(value(lua, "Distance()") - 75) < 1e-6,
          "square minimaps use the larger side as radius")


def test_minimap_resize():
    lua = boot()
    lua.execute("MINIMAP_WIDTH, MINIMAP_HEIGHT = 200, 200")
    lua.execute("BUTTON.scripts.OnUpdate(BUTTON)")
    check(abs(value(lua, "Distance()") - 105) < 1e-6,
          "button is repositioned when the minimap is resized")


def test_drag():
    lua = boot()
    lua.execute("PocketBankDB.settings.minimap.angle = 0; PB.UI.MinimapButton:Refresh()")
    check(value(lua, "BUTTON.point[4]") > 79, "angle 0 starts on the right edge")

    lua.execute("BUTTON.scripts.OnDragStart(BUTTON)")
    lua.execute("CURSOR = { 0, 100 }")
    lua.execute("BUTTON.scripts.OnUpdate(BUTTON)")
    check(abs(value(lua, "PocketBankDB.settings.minimap.angle") - 90) < 1e-6,
          "dragging above the minimap center saves angle 90")
    check(abs(value(lua, "Distance()") - 80) < 1e-6, "dragging keeps the button on the circle")

    lua.execute("BUTTON.scripts.OnDragStop(BUTTON)")
    check(value(lua, "BUTTON.dragging") is False, "dragging stops on drag release")


def test_tooltip():
    lua = boot()
    lua.execute("BUTTON.scripts.OnEnter(BUTTON)")
    check(value(lua, "GameTooltip.owner") is not None, "tooltip is owned by the button")
    check(value(lua, "GameTooltip.anchor") == "ANCHOR_LEFT", "tooltip anchors next to the button")
    check(value(lua, "GameTooltip.lines[1]") == "PocketBank", "tooltip shows the title")
    check(value(lua, "GameTooltip.lines[2]") == "Left click: open or close the window",
          "tooltip explains the left click")
    check(value(lua, "GameTooltip.lines[3]") == "Right click: options",
          "tooltip explains the right click")
    check(value(lua, "GameTooltip.lines[4]") == "Drag: move this button", "tooltip explains dragging")
    check(value(lua, "GameTooltip.shown") is True, "tooltip is shown on enter")

    lua.execute("BUTTON.scripts.OnLeave(BUTTON)")
    check(value(lua, "GameTooltip.shown") is False, "tooltip is hidden on leave")


def test_click_and_slash():
    lua = boot()
    lua.execute('BUTTON.scripts.OnClick(BUTTON, "LeftButton")')
    check(value(lua, "#CHAT") == 1, "clicking toggles the window through PB.ToggleWindow")
    check(value(lua, "CHAT[1]") == "The window is not available yet.",
          "clicking without a bank window warns the player")

    lua.execute("PB.UI.BankWindow = { Toggle = function() BANKWINDOW_TOGGLES = BANKWINDOW_TOGGLES + 1 end }")
    lua.execute('BUTTON.scripts.OnClick(BUTTON, "LeftButton")')
    check(value(lua, "BANKWINDOW_TOGGLES") == 1, "clicking calls the bank window Toggle")
    check(value(lua, "#CHAT") == 1, "no warning once the window exists")

    lua.execute('SlashCmdList["POCKETBANK"]("")')
    check(value(lua, "BANKWINDOW_TOGGLES") == 2, "/pb with no arguments toggles the window")
    lua.execute('SlashCmdList["POCKETBANK"]("version")')
    check(value(lua, "CHAT[#CHAT]") == "PocketBank dev", "/pb version prints the version")


def test_right_click():
    lua = boot()
    lua.execute('BUTTON.scripts.OnClick(BUTTON, "RightButton")')
    check(value(lua, "OPTIONS_OPENED") == 0, "right click opens nothing when the panel is missing")
    check(value(lua, "#CHAT") == 1, "right click without an options panel warns the player")
    check(value(lua, "CHAT[1]") == "PocketBank: the options panel is not available in this client.",
          "the warning names the missing options panel")
    check(value(lua, "BANKWINDOW_TOGGLES") == 0, "right click does not toggle the bank window")

    lua.execute("PB.UI.Options = {}")
    lua.execute('BUTTON.scripts.OnClick(BUTTON, "RightButton")')
    check(value(lua, "#CHAT") == 2, "an options table without Open still warns")

    lua.execute("PB.UI.Options = { Open = function() OPTIONS_OPENED = OPTIONS_OPENED + 1 end }")
    lua.execute('BUTTON.scripts.OnClick(BUTTON, "RightButton")')
    check(value(lua, "OPTIONS_OPENED") == 1, "right click calls PB.UI.Options.Open")
    check(value(lua, "#CHAT") == 2, "right click with an options panel is silent")
    check(value(lua, "BANKWINDOW_TOGGLES") == 0, "right click with a panel does not toggle the window")

    lua.execute("PB.UI.BankWindow = { Toggle = function() BANKWINDOW_TOGGLES = BANKWINDOW_TOGGLES + 1 end }")
    lua.execute('BUTTON.scripts.OnClick(BUTTON, "LeftButton")')
    check(value(lua, "BANKWINDOW_TOGGLES") == 1, "left click still toggles the window")
    check(value(lua, "OPTIONS_OPENED") == 1, "left click does not open the options")


def main():
    check_compiles()
    test_button_creation()
    test_icon_follows_addon_folder()
    test_angle_math()
    test_minimap_resize()
    test_drag()
    test_tooltip()
    test_click_and_slash()
    test_right_click()
    if failures:
        print(f"\n{len(failures)} check(s) failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
