local _, PB = ...

PB.UI = PB.UI or {}

local category

local function getSettings()
    if type(PocketBankDB) ~= "table" then
        return nil
    end
    local settings = PocketBankDB.settings
    if type(settings) ~= "table" then
        settings = {}
        PocketBankDB.settings = settings
    end
    return settings
end

local function minimapShown()
    local settings = getSettings()
    local minimap = settings and settings.minimap
    return not (type(minimap) == "table" and minimap.hide)
end

-- The client may call proxy setters as setter(value) or setter(setting, value).
local function setMinimapShown(setting, value)
    if value == nil then
        value = setting
    end
    local settings = getSettings()
    if settings then
        local minimap = settings.minimap
        if type(minimap) ~= "table" then
            minimap = {}
            settings.minimap = minimap
        end
        minimap.hide = not value
    end
    local button = PB.UI.MinimapButton
    if button and button.Refresh then
        button:Refresh()
    end
end

local function tooltipCounts()
    local settings = getSettings()
    if type(settings) ~= "table" then
        return true
    end
    return settings.tooltip ~= false
end

local function setTooltipCounts(setting, value)
    if value == nil then
        value = setting
    end
    local settings = getSettings()
    if settings then
        settings.tooltip = value and true or false
    end
end

local function register()
    if type(Settings) ~= "table"
        or type(Settings.RegisterVerticalLayoutCategory) ~= "function"
        or type(Settings.RegisterProxySetting) ~= "function"
        or type(Settings.CreateCheckbox) ~= "function"
        or type(Settings.RegisterAddOnCategory) ~= "function" then
        return
    end
    local ok, created = pcall(function()
        local panel = Settings.RegisterVerticalLayoutCategory(PB.L.WINDOW_TITLE)
        local minimapSetting = Settings.RegisterProxySetting(panel, "PocketBank_MinimapShown",
            "boolean", PB.L.OPT_MINIMAP, true, minimapShown, setMinimapShown)
        Settings.CreateCheckbox(panel, minimapSetting, PB.L.OPT_MINIMAP_TIP)
        local tooltipSetting = Settings.RegisterProxySetting(panel, "PocketBank_TooltipCounts",
            "boolean", PB.L.OPT_TOOLTIP, true, tooltipCounts, setTooltipCounts)
        Settings.CreateCheckbox(panel, tooltipSetting, PB.L.OPT_TOOLTIP_TIP)
        Settings.RegisterAddOnCategory(panel)
        return panel
    end)
    if ok then
        category = created
    end
end

local function open()
    local panel = category
    if panel and type(Settings) == "table" and type(Settings.OpenToCategory) == "function" then
        local ok, result
        if type(panel.GetID) == "function" then
            ok, result = pcall(Settings.OpenToCategory, panel:GetID())
        else
            ok, result = pcall(Settings.OpenToCategory, panel)
        end
        if ok and result ~= false then
            return
        end
    end
    print(PB.L.OPTIONS_UNAVAILABLE)
end

PB.UI.Options = { Open = open }

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_LOGIN")
frame:SetScript("OnEvent", function(self)
    self:UnregisterEvent("PLAYER_LOGIN")
    register()
end)
