"""Simulated-client checks for the PocketBank options panel."""

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
    "UI/Options.lua",
]

ALL_LUA = sorted(
    path.relative_to(ROOT).as_posix()
    for folder in ("Core", "Locales", "Modules", "UI")
    for path in (ROOT / folder).glob("*.lua")
)

UNAVAILABLE = "PocketBank: the options panel is not available in this client."

HARNESS = r"""
PB = {}
CHAT = {}
FRAMES = {}
BUTTON = nil
REFRESHES = 0
LOCALE = "enUS"

PocketBankDB = { schemaVersion = 1, chars = {} }

SETTINGS = { categories = {}, proxies = {}, checkboxes = {}, registered = {}, opened = {} }

function print(...)
    local parts = {}
    for i = 1, select("#", ...) do parts[i] = tostring((select(i, ...))) end
    CHAT[#CHAT + 1] = table.concat(parts, " ")
end

function GetLocale() return LOCALE end

Minimap = {}
function Minimap:GetWidth() return 150 end
function Minimap:GetHeight() return 150 end
function Minimap:GetMinimapShape() return "ROUND" end
function Minimap:GetCenter() return 0, 0 end
function Minimap:GetEffectiveScale() return 1 end

function CreateFrame(kind, name, parent)
    local frame = { kind = kind, name = name, parent = parent, scripts = {}, textures = {} }
    function frame:SetSize(width, height) self.width, self.height = width, height end
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

-- Minimal stand-in for the client Settings API, recording every call.
function InstallSettings()
    Settings = {}
    function Settings.RegisterVerticalLayoutCategory(name)
        local category = { name = name, id = #SETTINGS.categories + 1 }
        function category:GetID() return self.id end
        SETTINGS.categories[#SETTINGS.categories + 1] = category
        return category
    end
    function Settings.RegisterProxySetting(category, variable, kind, label, defaultValue, getter, setter)
        local setting = {
            category = category, variable = variable, kind = kind, label = label,
            defaultValue = defaultValue, getter = getter, setter = setter,
        }
        SETTINGS.proxies[#SETTINGS.proxies + 1] = setting
        return setting
    end
    function Settings.CreateCheckbox(category, setting, tooltip)
        SETTINGS.checkboxes[#SETTINGS.checkboxes + 1] = {
            category = category, setting = setting, tooltip = tooltip,
        }
    end
    function Settings.RegisterAddOnCategory(category)
        SETTINGS.registered[#SETTINGS.registered + 1] = category
    end
    function Settings.OpenToCategory(target)
        SETTINGS.opened[#SETTINGS.opened + 1] = target
    end
end

function SpyOnRefresh()
    local real = PB.UI.MinimapButton.Refresh
    PB.UI.MinimapButton.Refresh = function(self)
        REFRESHES = REFRESHES + 1
        return real(self)
    end
end
"""

failures = []


def check(condition, message):
    print(("PASS " if condition else "FAIL ") + message)
    if not condition:
        failures.append(message)


def boot(settings=True, fire=True, pre=""):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(HARNESS)
    if settings:
        lua.execute("InstallSettings()")
    if pre:
        lua.execute(pre)
    pb = lua.globals().PB
    for name in RUNTIME_FILES:
        source = (ROOT / name).read_text(encoding="utf-8")
        chunk = lua.eval("loadstring")(source, name)
        if chunk is None:
            raise SystemExit(f"cannot load {name}")
        chunk("PocketBank", pb)
    if fire:
        lua.execute('FireEvent("PLAYER_LOGIN")')
    return lua


def value(lua, expression):
    return lua.eval("function() return " + expression + " end")()


def last_message(lua):
    return value(lua, "CHAT[#CHAT]")


def check_compiles():
    lua = LuaRuntime(unpack_returned_tuples=True)
    loadstring = lua.eval("loadstring")
    for name in ALL_LUA:
        source = (ROOT / name).read_text(encoding="utf-8")
        check(loadstring(source, name) is not None, f"{name} compiles")


def test_toc_lists_the_file():
    files = [
        line.strip()
        for line in (ROOT / "PocketBank.toc").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    check("UI/Options.lua" in files, "UI/Options.lua is listed in PocketBank.toc")
    index = files.index("UI/Options.lua")
    check(index > 0 and files[index - 1] == "UI/MinimapButton.lua",
          "the options file loads right after the minimap button")


def test_panel_registered_on_login():
    lua = boot(fire=False)
    check(value(lua, "#SETTINGS.categories") == 0, "nothing is registered before PLAYER_LOGIN")
    lua.execute('FireEvent("PLAYER_LOGIN")')
    check(value(lua, "#SETTINGS.categories") == 1, "one options category after PLAYER_LOGIN")
    check(value(lua, "SETTINGS.categories[1].name") == "PocketBank", "the category is titled PocketBank")
    check(value(lua, "#SETTINGS.proxies") == 2, "two proxy settings")
    check(value(lua, "SETTINGS.proxies[1].variable") == "PocketBank_MinimapShown",
          "the minimap setting keeps its variable name")
    check(value(lua, "SETTINGS.proxies[1].kind") == "boolean", "the minimap setting is a boolean")
    check(value(lua, "SETTINGS.proxies[1].label") == "Show the minimap button",
          "the minimap setting is labelled in the player's language")
    check(value(lua, "SETTINGS.proxies[1].defaultValue") is True, "the minimap button defaults to shown")
    check(value(lua, "SETTINGS.proxies[1].category == SETTINGS.categories[1]") is True,
          "the minimap setting lives in the addon category")
    check(value(lua, "SETTINGS.proxies[2].variable") == "PocketBank_TooltipCounts",
          "the tooltip setting keeps its variable name")
    check(value(lua, "SETTINGS.proxies[2].kind") == "boolean", "the tooltip setting is a boolean")
    check(value(lua, "SETTINGS.proxies[2].label") == "Show counts in item tooltips",
          "the tooltip setting is labelled in the player's language")
    check(value(lua, "SETTINGS.proxies[2].defaultValue") is True, "the tooltip counts default to on")
    check(value(lua, "SETTINGS.proxies[2].category == SETTINGS.categories[1]") is True,
          "the tooltip setting lives in the addon category")

    check(value(lua, "#SETTINGS.checkboxes") == 2, "two checkboxes")
    check(value(lua, "SETTINGS.checkboxes[1].setting == SETTINGS.proxies[1]") is True,
          "the first checkbox drives the minimap setting")
    check(value(lua, "SETTINGS.checkboxes[1].category == SETTINGS.categories[1]") is True,
          "the first checkbox is added to the category")
    check(value(lua, "SETTINGS.checkboxes[1].tooltip") ==
          "Shows the PocketBank button around the minimap. Type /pb to open the window without it.",
          "the minimap checkbox explains itself")
    check(value(lua, "SETTINGS.checkboxes[2].setting == SETTINGS.proxies[2]") is True,
          "the second checkbox drives the tooltip setting")
    check(value(lua, "SETTINGS.checkboxes[2].tooltip") ==
          "Adds to item tooltips how many each character of your account holds in the bank, bags and gear.",
          "the tooltip checkbox explains itself")
    check(value(lua, "#SETTINGS.registered") == 1 and
          value(lua, "SETTINGS.registered[1] == SETTINGS.categories[1]") is True,
          "the category is handed to the client")

    lua.execute('FireEvent("PLAYER_LOGIN")')
    check(value(lua, "#SETTINGS.categories") == 1 and value(lua, "#SETTINGS.proxies") == 2,
          "the panel is registered only once")


def test_minimap_setting():
    lua = boot()
    lua.execute("SpyOnRefresh()")
    check(value(lua, "SETTINGS.proxies[1].getter()") is True, "the minimap button is on by default")
    check(value(lua, "PocketBankDB.settings.minimap.hide") is False, "nothing is hidden by default")

    lua.execute("PocketBankDB.settings.minimap.hide = true")
    check(value(lua, "SETTINGS.proxies[1].getter()") is False, "a hidden button reads as off")

    lua.execute("SETTINGS.proxies[1].setter(false)")
    check(value(lua, "PocketBankDB.settings.minimap.hide") is True,
          "unchecking the box hides the button")
    check(value(lua, "REFRESHES") == 1, "the minimap button is refreshed after the change")
    check(value(lua, "BUTTON.shown") is False, "the button is hidden right away")

    lua.execute("SETTINGS.proxies[1].setter(SETTINGS.proxies[1], true)")
    check(value(lua, "PocketBankDB.settings.minimap.hide") is False,
          "checking it back (setting, value) shows the button again")
    check(value(lua, "REFRESHES") == 2, "the button is refreshed again")
    check(value(lua, "BUTTON.shown") is True, "the button is shown right away")

    lua.execute("PocketBankDB.settings = nil\nSETTINGS.proxies[1].setter(true)")
    check(value(lua, "PocketBankDB.settings.minimap.hide") is False,
          "the settings tables are created on demand")
    lua.execute("SETTINGS.proxies[1].setter(false)")
    check(value(lua, "PocketBankDB.settings.minimap.hide") is True,
          "the new tables keep the change")


def test_tooltip_setting():
    lua = boot()
    lua.execute("SpyOnRefresh()")
    check(value(lua, "SETTINGS.proxies[2].getter()") is True, "the tooltip counts are on by default")

    lua.execute("SETTINGS.proxies[2].setter(false)")
    check(value(lua, "PocketBankDB.settings.tooltip") is False, "unchecking the box stores false")
    check(value(lua, "SETTINGS.proxies[2].getter()") is False, "the stored false reads as off")

    lua.execute("SETTINGS.proxies[2].setter(SETTINGS.proxies[2], true)")
    check(value(lua, "PocketBankDB.settings.tooltip") is True, "checking it back (setting, value) stores true")
    check(value(lua, "SETTINGS.proxies[2].getter()") is True, "the stored true reads as on")

    lua.execute("SETTINGS.proxies[2].setter(false)")
    check(value(lua, "PocketBankDB.settings.tooltip") is False, "the box can be unchecked again")
    check(value(lua, "REFRESHES") == 0, "the tooltip box leaves the minimap button alone")

    lua.execute("PocketBankDB.settings.tooltip = nil")
    check(value(lua, "SETTINGS.proxies[2].getter()") is True, "a setting that was never saved keeps the counts")
    lua.execute("PocketBankDB.settings = nil")
    check(value(lua, "SETTINGS.proxies[2].getter()") is True, "missing settings keep the counts")

    lua.execute("PocketBankDB = nil")
    check(value(lua, "SETTINGS.proxies[2].getter()") is True, "the getter does not need a saved database")


def test_slash_opens_the_panel():
    lua = boot()
    lua.execute('SlashCmdList["POCKETBANK"]("options")')
    check(value(lua, "#SETTINGS.opened") == 1, "/pb options opens the panel")
    check(value(lua, "SETTINGS.opened[1]") == 1, "the panel is opened by its category id")
    check(value(lua, "#CHAT") == 0, "/pb options prints nothing when the panel opens")

    lua.execute('SlashCmdList["POCKETBANK"]("opciones")')
    check(value(lua, "#SETTINGS.opened") == 2, "/pb opciones opens the panel too")
    check(value(lua, "SETTINGS.opened[2]") == 1, "the Spanish alias opens the same category")

    lua.execute('SlashCmdList["POCKETBANK"](" OPTIONS ")')
    check(value(lua, "#SETTINGS.opened") == 3, "the command ignores case and spaces")

    lua.execute("CATEGORY = SETTINGS.categories[1]; SETTINGS.categories[1].GetID = nil")
    lua.execute("PB.UI.Options.Open()")
    check(value(lua, "SETTINGS.opened[4] == CATEGORY") is True,
          "the category table is passed when it has no GetID")
    check(value(lua, "#CHAT") == 0, "opening a registered panel never warns")


def test_open_failures():
    lua = boot()
    lua.execute("Settings.OpenToCategory = function() return false end")
    lua.execute('SlashCmdList["POCKETBANK"]("options")')
    check(last_message(lua) == UNAVAILABLE, "a refused OpenToCategory warns the player")
    check(value(lua, "#SETTINGS.opened") == 0, "the refused call is not counted")

    lua.execute("Settings.OpenToCategory = function() error('no options') end")
    count = value(lua, "#CHAT")
    lua.execute('SlashCmdList["POCKETBANK"]("opciones")')
    check(value(lua, "#CHAT") == count + 1, "an OpenToCategory that errors warns the player")
    check(last_message(lua) == UNAVAILABLE, "the error does not reach the player as a Lua error")

    lua.execute("Settings.OpenToCategory = nil")
    lua.execute('SlashCmdList["POCKETBANK"]("options")')
    check(last_message(lua) == UNAVAILABLE, "a client without OpenToCategory warns the player")


def test_without_settings_api():
    lua = boot(settings=False)
    check(value(lua, "type(Settings)") == "nil", "this client has no Settings API")
    check(value(lua, "BUTTON ~= nil") is True, "the addon still builds its minimap button")
    check(value(lua, "#SETTINGS.categories") == 0, "nothing is registered")
    lua.execute('SlashCmdList["POCKETBANK"]("options")')
    check(last_message(lua) == UNAVAILABLE, "/pb options reports the missing panel")
    check(value(lua, "#CHAT") == 1, "the warning is printed once")
    lua.execute("PB.UI.Options.Open()")
    check(value(lua, "#CHAT") == 2, "calling Open directly reports the missing panel too")

    lua.execute("PocketBankDB.settings.minimap.hide = true\nREFRESHES = 0")
    lua.execute('BUTTON.scripts.OnClick(BUTTON, "LeftButton")')
    check(value(lua, "#CHAT") == 3, "the window still toggles without the API")


def test_partial_settings_api():
    lua = boot(
        settings=False,
        pre="Settings = { RegisterVerticalLayoutCategory = function() return { GetID = function() return 1 end } end }",
    )
    check(value(lua, "#SETTINGS.categories") == 0, "an incomplete API registers no category")
    lua.execute('SlashCmdList["POCKETBANK"]("options")')
    check(last_message(lua) == UNAVAILABLE, "an incomplete API still warns instead of erroring")


def test_registration_error_is_contained():
    lua = boot(
        settings=False,
        pre="InstallSettings(); Settings.CreateCheckbox = function() error('boom') end",
    )
    check(value(lua, "#SETTINGS.categories") == 1, "the category is created before the failing call")
    check(value(lua, "#SETTINGS.checkboxes") == 0, "the failing call stops the checkboxes")
    check(value(lua, "#SETTINGS.registered") == 0, "a half-built panel is not handed to the client")
    lua.execute('SlashCmdList["POCKETBANK"]("options")')
    check(last_message(lua) == UNAVAILABLE, "a failed registration warns instead of erroring")


def main():
    check_compiles()
    test_toc_lists_the_file()
    test_panel_registered_on_login()
    test_minimap_setting()
    test_tooltip_setting()
    test_slash_opens_the_panel()
    test_open_failures()
    test_without_settings_api()
    test_partial_settings_api()
    test_registration_error_is_contained()
    if failures:
        print(f"\n{len(failures)} check(s) failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
