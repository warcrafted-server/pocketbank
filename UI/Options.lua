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

local function plainName(entry)
    local char = entry.char
    if type(char) ~= "table" then
        char = {}
    end
    return char.fullName or char.name or entry.key
end

local function classColoredName(entry)
    local name = plainName(entry)
    local class = type(entry.char) == "table" and entry.char.class
    local colors = RAID_CLASS_COLORS and class and RAID_CLASS_COLORS[class]
    if colors and colors.colorStr then
        return "|c" .. colors.colorStr .. name .. "|r"
    end
    return name
end

local function otherChars()
    local list = {}
    if type(PB.DB) ~= "table" or type(PB.DB.ListChars) ~= "function" then
        return list
    end
    local ok, chars = pcall(PB.DB.ListChars)
    if not ok or type(chars) ~= "table" then
        return list
    end
    local current
    if type(PB.DB.GetCharKey) == "function" then
        local got, key = pcall(PB.DB.GetCharKey)
        if got then current = key end
    end
    for i = 1, #chars do
        local entry = chars[i]
        if type(entry) == "table" and entry.key ~= current then
            list[#list + 1] = entry
        end
    end
    return list
end

local function onDeleteAccept(dialog, data)
    local target = data
    if type(target) ~= "table" and type(dialog) == "table" then
        target = dialog.data
    end
    if type(target) ~= "table" or type(target.key) ~= "string" then
        return
    end
    if type(PB.DB) ~= "table" or type(PB.DB.DeleteChar) ~= "function" then
        return
    end
    local ok, deleted = pcall(PB.DB.DeleteChar, target.key)
    if ok and deleted then
        print(string.format(PB.L.CHAR_DELETED, target.name or target.key))
    end
end

local dialogRegistered = false

local function registerDialog()
    if dialogRegistered or type(StaticPopupDialogs) ~= "table" then
        return
    end
    dialogRegistered = true
    StaticPopupDialogs.POCKETBANK_DELETE_CHAR = {
        text = PB.L.DELETE_CONFIRM,
        button1 = YES or ACCEPT or "OK",
        button2 = NO or CANCEL,
        OnAccept = onDeleteAccept,
        timeout = 0,
        whileDead = true,
        hideOnEscape = true,
        showAlert = true,
        preferredIndex = 3,
    }
end

local function confirmDelete(entry)
    if type(entry) ~= "table" or entry.key == nil then
        return
    end
    if type(StaticPopupDialogs) ~= "table" or type(StaticPopup_Show) ~= "function" then
        print(PB.L.OPTIONS_UNAVAILABLE)
        return
    end
    registerDialog()
    local ok = pcall(StaticPopup_Show, "POCKETBANK_DELETE_CHAR", classColoredName(entry), nil, {
        key = entry.key,
        name = plainName(entry),
    })
    if not ok then
        print(PB.L.OPTIONS_UNAVAILABLE)
    end
end

local function onDeleteClick()
    local entries = otherChars()
    if #entries == 0 then
        print(PB.L.DELETE_NONE)
        return
    end
    if type(MenuUtil) ~= "table" or type(MenuUtil.CreateContextMenu) ~= "function" then
        print(PB.L.OPTIONS_UNAVAILABLE)
        return
    end

    local owner = UIParent
    if type(GetMouseFoci) == "function" then
        local ok, foci = pcall(GetMouseFoci)
        if ok and type(foci) == "table" and foci[1] ~= nil then
            owner = foci[1]
        end
    end

    local function generator(_, root)
        if type(root) ~= "table" then
            return
        end
        if type(root.CreateTitle) == "function" then
            pcall(root.CreateTitle, root, PB.L.OPT_DELETE)
        end
        if type(root.CreateButton) ~= "function" then
            return
        end
        for i = 1, #entries do
            local entry = entries[i]
            pcall(root.CreateButton, root, classColoredName(entry), function()
                confirmDelete(entry)
            end)
        end
    end

    pcall(MenuUtil.CreateContextMenu, owner, generator)
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
        local panel, layout = Settings.RegisterVerticalLayoutCategory(PB.L.WINDOW_TITLE)
        local minimapSetting = Settings.RegisterProxySetting(panel, "PocketBank_MinimapShown",
            "boolean", PB.L.OPT_MINIMAP, true, minimapShown, setMinimapShown)
        Settings.CreateCheckbox(panel, minimapSetting, PB.L.OPT_MINIMAP_TIP)
        local tooltipSetting = Settings.RegisterProxySetting(panel, "PocketBank_TooltipCounts",
            "boolean", PB.L.OPT_TOOLTIP, true, tooltipCounts, setTooltipCounts)
        Settings.CreateCheckbox(panel, tooltipSetting, PB.L.OPT_TOOLTIP_TIP)
        -- A client missing the initializers or the menu must never lose the
        -- checkboxes above, so the extra rows stay behind type checks.
        if type(layout) == "table" and type(layout.AddInitializer) == "function" then
            pcall(function()
                if type(CreateSettingsListSectionHeaderInitializer) == "function" then
                    layout:AddInitializer(CreateSettingsListSectionHeaderInitializer(PB.L.OPT_SECTION_DATA))
                end
                if type(CreateSettingsButtonInitializer) == "function" then
                    layout:AddInitializer(CreateSettingsButtonInitializer(PB.L.OPT_DELETE,
                        PB.L.OPT_DELETE_BUTTON, onDeleteClick, PB.L.OPT_DELETE_TIP, true))
                end
            end)
        end
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

registerDialog()

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_LOGIN")
frame:SetScript("OnEvent", function(self)
    self:UnregisterEvent("PLAYER_LOGIN")
    register()
end)
