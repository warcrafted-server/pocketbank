local ADDON, PB = ...

PB.UI = PB.UI or {}

local MinimapButton = {}
PB.UI.MinimapButton = MinimapButton

local BUTTON_NAME = "PocketBankMinimapButton"
local ICON = "Interface\\AddOns\\" .. ADDON .. "\\Media\\logo"
local BORDER = "Interface\\Minimap\\MiniMap-TrackingBorder"
local BACKGROUND = "Interface\\Minimap\\UI-Minimap-Background"
local HIGHLIGHT = "Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight"
local DEFAULT_ANGLE = 225

local button
local lastWidth, lastHeight

local function getSettings()
    if type(PocketBankDB) ~= "table" then
        return nil
    end
    local settings = PocketBankDB.settings
    if type(settings) ~= "table" then
        settings = {}
        PocketBankDB.settings = settings
    end
    local minimap = settings.minimap
    if type(minimap) ~= "table" then
        minimap = {}
        settings.minimap = minimap
    end
    if minimap.hide == nil then
        minimap.hide = false
    end
    minimap.angle = tonumber(minimap.angle) or DEFAULT_ANGLE
    if minimap.angle < 0 then
        minimap.angle = minimap.angle + 360
    end
    if minimap.angle >= 360 then
        minimap.angle = minimap.angle % 360
    end
    return minimap
end

local function updatePosition()
    if not button or not Minimap then
        return
    end
    local width = Minimap.GetWidth and Minimap:GetWidth() or 150
    local height = Minimap.GetHeight and Minimap:GetHeight() or width
    local radius = width / 2 + 5
    if Minimap.GetMinimapShape then
        local ok, shape = pcall(Minimap.GetMinimapShape, Minimap)
        if ok and shape == "SQUARE" then
            radius = math.max(width, height) / 2 + 5
        end
    end
    local settings = getSettings()
    local angle = math.rad(settings and settings.angle or DEFAULT_ANGLE)
    button:ClearAllPoints()
    button:SetPoint("CENTER", Minimap, "CENTER", math.cos(angle) * radius, math.sin(angle) * radius)
end

local function updateDrag(self)
    if not self.dragging or not Minimap or type(GetCursorPosition) ~= "function" then
        return
    end
    local mx, my = GetCursorPosition()
    local scale = Minimap.GetEffectiveScale and Minimap:GetEffectiveScale() or 1
    mx, my = mx / scale, my / scale
    local cx, cy = Minimap:GetCenter()
    if not cx or not cy then
        return
    end
    local angle = math.deg(math.atan2(my - cy, mx - cx))
    if angle < 0 then
        angle = angle + 360
    end
    local settings = getSettings()
    if settings then
        settings.angle = angle
    end
    updatePosition()
end

local function onUpdate(self)
    if self.dragging then
        updateDrag(self)
    end
    -- The client fires no event when the minimap is resized, so poll its size.
    local width = Minimap.GetWidth and Minimap:GetWidth() or 0
    local height = Minimap.GetHeight and Minimap:GetHeight() or width
    if width ~= lastWidth or height ~= lastHeight then
        lastWidth, lastHeight = width, height
        updatePosition()
    end
end

local function showTooltip(owner)
    if not GameTooltip then
        return
    end
    GameTooltip:SetOwner(owner, "ANCHOR_LEFT")
    GameTooltip:AddLine(PB.L.MINIMAP_TOOLTIP_TITLE, 1, 1, 1)
    GameTooltip:AddLine(PB.L.MINIMAP_TOOLTIP_LEFT, 1, 1, 1, true)
    GameTooltip:AddLine(PB.L.MINIMAP_TOOLTIP_RIGHT, 1, 1, 1, true)
    GameTooltip:AddLine(PB.L.MINIMAP_TOOLTIP_DRAG, 0.7, 0.7, 0.7, true)
    GameTooltip:Show()
end

local function createButton()
    if button or not Minimap then
        return
    end

    local b = CreateFrame("Button", BUTTON_NAME, Minimap)
    button = b
    b:SetSize(31, 31)
    b:SetFrameStrata("MEDIUM")
    b:SetFrameLevel(8)
    b:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    b:RegisterForDrag("LeftButton")

    local background = b:CreateTexture(nil, "BACKGROUND")
    background:SetTexture(BACKGROUND)
    background:SetSize(20, 20)
    background:SetPoint("CENTER")

    local icon = b:CreateTexture(nil, "ARTWORK")
    icon:SetTexture(ICON)
    icon:SetSize(20, 20)
    icon:SetPoint("CENTER")

    local border = b:CreateTexture(nil, "OVERLAY")
    border:SetTexture(BORDER)
    border:SetSize(53, 53)
    border:SetPoint("TOPLEFT")

    local highlight = b:CreateTexture(nil, "HIGHLIGHT")
    highlight:SetTexture(HIGHLIGHT)
    highlight:SetBlendMode("ADD")
    highlight:SetSize(31, 31)
    highlight:SetPoint("TOPLEFT")

    b:SetScript("OnEnter", function(self)
        showTooltip(self)
    end)
    b:SetScript("OnLeave", function()
        if GameTooltip then
            GameTooltip:Hide()
        end
    end)
    b:SetScript("OnClick", function(_, mouseButton)
        if mouseButton == "RightButton" then
            local options = PB.UI.Options
            if options and options.Open then
                options.Open()
            else
                print(PB.L.OPTIONS_UNAVAILABLE)
            end
            return
        end
        PB.ToggleWindow()
    end)
    b:SetScript("OnDragStart", function(self)
        self.dragging = true
    end)
    b:SetScript("OnDragStop", function(self)
        self.dragging = false
        updatePosition()
    end)
    b:SetScript("OnUpdate", onUpdate)

    MinimapButton:Refresh()
end

function MinimapButton:Refresh()
    if not button then
        return
    end
    local settings = getSettings()
    if settings and settings.hide then
        button:Hide()
        return
    end
    button:Show()
    updatePosition()
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_LOGIN")
frame:SetScript("OnEvent", function(self)
    self:UnregisterEvent("PLAYER_LOGIN")
    createButton()
end)
