local ADDON, PB = ...

-- Read-only copy of the client's character sheet (PaperDollFrame). Sizes,
-- offsets and textures come from a /pb paperdoll dump of build 1.60.1.

PB.UI = PB.UI or {}

local EquipmentView = {}
PB.UI.EquipmentView = EquipmentView

EquipmentView.WIDTH, EquipmentView.HEIGHT = 398, 484

local SLOT_SIZE = 37
local SLOT_STEP = SLOT_SIZE + 6
local SLOT_TOP = -60
local SLOT_LEFT, SLOT_RIGHT = 24, -20
local SCENE_TOP = -56
local SCENE_WIDTH, SCENE_HEIGHT = 398, 428
local QUALITY_BORDER = 130839
local SLOT_HIGHLIGHT = 130718
local ROTATE_SPEED = 0.02

local LEFT = { "HeadSlot", "NeckSlot", "ShoulderSlot", "BackSlot", "ChestSlot", "ShirtSlot", "TabardSlot", "WristSlot" }
local RIGHT = { "HandsSlot", "WaistSlot", "LegsSlot", "FeetSlot", "Finger0Slot", "Finger1Slot", "Trinket0Slot", "Trinket1Slot" }
local WEAPONS = { "MainHandSlot", "SecondaryHandSlot", "RangedSlot" }
-- Used when GetInventorySlotInfo fails; values checked in build 1.60.1.
local SLOT_IDS = {
    HeadSlot = 1, NeckSlot = 2, ShoulderSlot = 3, ShirtSlot = 4, ChestSlot = 5, WaistSlot = 6, LegsSlot = 7,
    FeetSlot = 8, WristSlot = 9, HandsSlot = 10, Finger0Slot = 11, Finger1Slot = 12, Trinket0Slot = 13,
    Trinket1Slot = 14, BackSlot = 15, MainHandSlot = 16, SecondaryHandSlot = 17, RangedSlot = 18, TabardSlot = 19,
}
-- The race background is drawn in four parts, like the client's.
local RACE_PARTS = {
    { 0, 0, 319, 299 }, { 319, 0, 79, 299 }, { 0, -299, 319, 129 }, { 319, -299, 79, 129 },
}

local L = PB.L
local view

local function helpers() return PB.UI.ItemButton end

local function hideComparison()
    for _, name in ipairs({ "ShoppingTooltip1", "ShoppingTooltip2" }) do
        local tip = _G[name]
        if tip and tip.Hide then tip:Hide() end
    end
end

-- Gear needs no comparison: the logged-in character's own pieces use the
-- character sheet tooltip (durability, no compare), other characters' pieces
-- are not compared against the current gear.
local function slotOnEnter(self)
    if not GameTooltip or not (self.link or view.isPlayer) then return end
    GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
    if view.isPlayer and self.slotId and type(GameTooltip.SetInventoryItem) == "function" then
        local ok, hasItem = pcall(GameTooltip.SetInventoryItem, GameTooltip, "player", self.slotId)
        if not ok or not hasItem then
            if not self.link then GameTooltip:Hide() return end
            pcall(GameTooltip.SetHyperlink, GameTooltip, self.link)
        end
    else
        view.savedCompare = GameTooltip.supportsItemComparison
        GameTooltip.supportsItemComparison = false
        pcall(GameTooltip.SetHyperlink, GameTooltip, self.link)
    end
    GameTooltip:Show()
    hideComparison()
end

local function slotOnLeave()
    if GameTooltip then
        GameTooltip.supportsItemComparison = view.savedCompare
        view.savedCompare = nil
        GameTooltip:Hide()
    end
    hideComparison()
end

local function slotInfo(name)
    local ok, id, texture = pcall(GetInventorySlotInfo, name)
    if ok and id then return id, texture end
    return SLOT_IDS[name]
end

local function createSlot(parent, name)
    local h = helpers()
    local slot = CreateFrame("Button", nil, parent)
    slot:SetSize(SLOT_SIZE, SLOT_SIZE)
    slot:SetFrameLevel(parent:GetFrameLevel() + 3)
    slot:RegisterForClicks("LeftButtonUp", "RightButtonUp")
    slot.slotId, slot.emptyIcon = slotInfo(name)

    local bg = slot:CreateTexture(nil, "BACKGROUND")
    bg:SetPoint("CENTER")
    bg:SetSize(55, 55)
    h.SetAtlas(bg, "UI-Character-Info-GearSlot")

    local icon = slot:CreateTexture(nil, "BORDER")
    icon:SetAllPoints()
    slot.icon = icon

    local quality = slot:CreateTexture(nil, "OVERLAY")
    quality:SetAllPoints()
    quality:SetTexture(QUALITY_BORDER)
    quality:Hide()
    slot.quality = quality

    local highlight = slot:CreateTexture(nil, "HIGHLIGHT")
    highlight:SetAllPoints()
    highlight:SetTexture(SLOT_HIGHLIGHT)
    highlight:SetBlendMode("ADD")

    slot:SetScript("OnEnter", slotOnEnter)
    slot:SetScript("OnLeave", slotOnLeave)
    slot:SetScript("OnClick", h.OnClick)
    return slot
end

local function fillSlot(slot, item)
    slot.link = item and item.link or nil
    slot.icon:SetTexture(item and item.icon or slot.emptyIcon)
    local r, g, b
    if item and (item.quality or 0) >= 2 then r, g, b = helpers().QualityColor(item.quality) end
    if r then
        slot.quality:SetVertexColor(r, g, b)
        slot.quality:Show()
    else
        slot.quality:Hide()
    end
end

local function createModel(parent)
    local ok, model = pcall(CreateFrame, "DressUpModel", nil, parent)
    if not ok or not model then return nil end
    model:SetSize(SCENE_WIDTH, SCENE_HEIGHT)
    model:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, SCENE_TOP)
    model:SetFrameLevel(parent:GetFrameLevel() + 1)
    -- Drag to turn the model, as in the character sheet.
    model:EnableMouse(true)
    model:SetScript("OnMouseDown", function(self)
        self.dragX = GetCursorPosition()
    end)
    model:SetScript("OnMouseUp", function(self) self.dragX = nil end)
    model:SetScript("OnUpdate", function(self)
        if not self.dragX then return end
        local x = GetCursorPosition()
        self.facing = (self.facing or 0) + (x - self.dragX) * ROTATE_SPEED
        self.dragX = x
        pcall(self.SetFacing, self, self.facing)
    end)
    return model
end

local function create(parent)
    local h = helpers()
    view = { regions = {}, slots = {} }

    -- Backgrounds are regions of the window itself so its metal border,
    -- a child frame, stays on top of them.
    local general = parent:CreateTexture(nil, "BACKGROUND", nil, 1)
    general:SetPoint("TOPLEFT", 0, -20)
    general:SetSize(SCENE_WIDTH, 464)
    h.SetAtlas(general, "UI-Character-Info-General-BG")
    view.regions[#view.regions + 1] = general

    view.race = {}
    for i, part in ipairs(RACE_PARTS) do
        local t = parent:CreateTexture(nil, "BACKGROUND", nil, 2)
        t:SetPoint("TOPLEFT", parent, "TOPLEFT", part[1], SCENE_TOP + part[2])
        t:SetSize(part[3], part[4])
        view.race[i] = t
        view.regions[#view.regions + 1] = t
    end

    local overlay = parent:CreateTexture(nil, "BORDER", nil, 1)
    overlay:SetPoint("TOPLEFT", 0, SCENE_TOP)
    overlay:SetSize(SCENE_WIDTH, SCENE_HEIGHT)
    h.SetAtlas(overlay, "UI-Character-Info-RaceBG-Overlay")
    view.regions[#view.regions + 1] = overlay

    view.model = createModel(parent)

    for i, name in ipairs(LEFT) do
        local slot = createSlot(parent, name)
        slot:SetPoint("TOPLEFT", parent, "TOPLEFT", SLOT_LEFT, SLOT_TOP - (i - 1) * SLOT_STEP)
        view.slots[#view.slots + 1] = slot
    end
    for i, name in ipairs(RIGHT) do
        local slot = createSlot(parent, name)
        slot:SetPoint("TOPRIGHT", parent, "TOPRIGHT", SLOT_RIGHT, SLOT_TOP - (i - 1) * SLOT_STEP)
        view.slots[#view.slots + 1] = slot
    end
    local previous
    for _, name in ipairs(WEAPONS) do
        local slot = createSlot(parent, name)
        if previous then
            slot:SetPoint("TOPLEFT", previous, "TOPRIGHT", 6, 0)
        else
            slot:SetPoint("BOTTOM", parent, "BOTTOM", -40, 30)
        end
        previous = slot
        view.slots[#view.slots + 1] = slot
    end

    local front = CreateFrame("Frame", nil, parent)
    front:SetFrameLevel(parent:GetFrameLevel() + 5)
    front:SetAllPoints()
    view.front = front

    local level = front:CreateFontString(nil, "OVERLAY", "GameFontNormalMed2Outline")
    level:SetPoint("TOP", parent, "TOP", 0, SCENE_TOP - 10)
    view.level = level

    local noModel = front:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
    noModel:SetPoint("CENTER", parent, "TOPLEFT", SCENE_WIDTH / 2, SCENE_TOP - SCENE_HEIGHT / 2)
    noModel:SetWidth(SCENE_WIDTH - 160)
    noModel:SetText(L.NO_MODEL)
    view.noModel = noModel

    local notice = CreateFrame("Frame", nil, front)
    notice:SetSize(SCENE_WIDTH - 140, 60)
    notice:SetPoint("CENTER", parent, "TOPLEFT", SCENE_WIDTH / 2, SCENE_TOP - SCENE_HEIGHT / 2)
    local shade = notice:CreateTexture(nil, "BACKGROUND")
    shade:SetAllPoints()
    shade:SetColorTexture(0, 0, 0, 0.75)
    local text = notice:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
    text:SetPoint("CENTER")
    text:SetWidth(SCENE_WIDTH - 160)
    view.notice, view.noticeText = notice, text
end

local function levelLine(char)
    local className = char.className
        or (LOCALIZED_CLASS_NAMES_MALE and char.class and LOCALIZED_CLASS_NAMES_MALE[char.class])
        or char.class or ""
    local colors = RAID_CLASS_COLORS and char.class and RAID_CLASS_COLORS[char.class]
    if colors and colors.colorStr then className = "|c" .. colors.colorStr .. className .. "|r" end
    local line = string.gsub(L.LEVEL_LINE, "{level}", tostring(char.level or "?"))
    return (string.gsub(line, "{class}", function() return className end))
end

local function setRaceBackground(race)
    local shown = false
    for i, t in ipairs(view.race) do
        local ok, loaded = false, false
        if race then
            ok, loaded = pcall(t.SetTexture, t, "Interface\\DressUpFrame\\DressUpBackground-" .. race .. i)
        end
        -- SetTexture returns false for a file the client does not have.
        local visible = ok and loaded ~= false and race ~= nil
        t:SetShown(visible)
        shown = shown or visible
    end
    return shown
end

-- Only the logged-in character can be rendered as it is. Another character
-- of the same race and sex is shown with the current body wearing its saved
-- gear; this client has no way to load another race (no SetCustomRace).
local function dressModel(char, items, isPlayer)
    local model = view.model
    if not model then return end
    if isPlayer then
        model:SetShown(pcall(model.SetUnit, model, "player"))
        return
    end
    local _, playerRace = UnitRace("player")
    if not char.race or char.race ~= playerRace or char.sex ~= UnitSex("player") then
        model:Hide()
        return
    end
    model:Show()
    pcall(model.SetUnit, model, "player")
    pcall(model.Undress, model)
    for _, item in pairs(items) do
        if item.link then pcall(model.TryOn, model, item.link) end
    end
    -- The character sheet shows weapons sheathed.
    pcall(model.SetSheathed, model, true)
end

function EquipmentView:Show(parent, char, isPlayer)
    if not view then create(parent) end
    view.isPlayer = isPlayer
    for _, region in ipairs(view.regions) do region:Show() end
    view.front:Show()

    local equipment = char and char.equipment
    local items = equipment and equipment.slots or {}
    for _, slot in ipairs(view.slots) do
        slot:Show()
        fillSlot(slot, slot.slotId and items[slot.slotId])
    end

    setRaceBackground(char and char.race)
    view.level:SetText(char and levelLine(char) or "")
    if view.model then
        if char then dressModel(char, items, isPlayer) else view.model:Hide() end
    end

    view.notice:SetShown(equipment == nil)
    view.noModel:SetShown(equipment ~= nil and not (view.model and view.model:IsShown()))
    view.noticeText:SetText(isPlayer and L.NO_EQUIP_DATA or L.NO_EQUIP_DATA_OTHER)
end

function EquipmentView:Hide()
    if not view then return end
    for _, region in ipairs(view.regions) do region:Hide() end
    for _, slot in ipairs(view.slots) do slot:Hide() end
    if view.model then view.model:Hide() end
    view.front:Hide()
end
