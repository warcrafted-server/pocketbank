local ADDON, PB = ...

-- Read-only copy of the client's bank window (BankFrame/BankPanel). Sizes,
-- offsets and atlases come from a /pb frames dump of the real window in
-- build 1.60.1, so the layout matches it slot for slot.

PB.UI = PB.UI or {}

local BankWindow = {}
PB.UI.BankWindow = BankWindow

local FRAME_NAME = "PocketBankFrame"
local WIDTH, HEIGHT = 480, 460
local COLUMNS, ROWS = 8, 6
local SLOT_SIZE = 37
local SLOT_LEFT, SLOT_TOP = 47, -63
local SLOT_GAP_X, SLOT_GAP_Y = 13, 10
local ROW_STEP = SLOT_SIZE + SLOT_GAP_Y
local SIDE_TAB_SIZE = 55
local SIDE_TAB_STEP = SIDE_TAB_SIZE + 5
local CHEST_ICON = 8197077 -- icon of the client's own bank side tab
local BAG_ICON = "Interface\\Icons\\INV_Misc_Bag_08"
local EQUIPMENT_ICON = "Interface\\Icons\\INV_Helmet_03"
local QUALITY_BORDER = 130839
local SLOT_HIGHLIGHT = 130718
local ROCK_BACKGROUND = 374155
local SEARCH_SLOT_ATLAS = "bags-item-slot64"

local L = PB.L
local frame
local slots = {}
local charKey
local searchText = ""

-- Each view is one saved section of the character shown in the same grid.
local VIEWS = {
    { key = "bank", icon = CHEST_ICON, label = "BANK", title = "BANK_TITLE",
      empty = "NO_DATA", emptyOther = "NO_DATA_OTHER", slotAtlas = "bags-item-bankslot64" },
    { key = "bags", icon = BAG_ICON, label = "BAGS", title = "BAGS_TITLE",
      empty = "NO_BAG_DATA", emptyOther = "NO_BAG_DATA_OTHER", slotAtlas = "bags-item-slot64" },
    { key = "equipment", icon = EQUIPMENT_ICON, label = "EQUIPMENT", paperdoll = true },
}
local view = VIEWS[1]

local function setAtlas(texture, atlas, useSize)
    if texture and type(texture.SetAtlas) == "function" then
        return pcall(texture.SetAtlas, texture, atlas, useSize) and true or false
    end
    return false
end

local function qualityColor(quality)
    if C_Item and C_Item.GetItemQualityColor then
        local ok, r, g, b = pcall(C_Item.GetItemQualityColor, quality)
        if ok and r then return r, g, b end
    end
    local color = ITEM_QUALITY_COLORS and ITEM_QUALITY_COLORS[quality]
    if color then return color.r, color.g, color.b end
end

local function currentChar()
    if not PB.DB then return nil end
    if charKey then return PB.DB.GetCharByKey(charKey) end
    return PB.DB.GetChar(false)
end

-- Item slots ---------------------------------------------------------------

local function slotOnEnter(self)
    if not self.link or not GameTooltip then return end
    GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
    pcall(GameTooltip.SetHyperlink, GameTooltip, self.link)
    GameTooltip:Show()
end

local function slotOnLeave()
    if GameTooltip then GameTooltip:Hide() end
end

local function linkInChat(link)
    if type(ChatEdit_InsertLink) == "function" then
        local ok, inserted = pcall(ChatEdit_InsertLink, link)
        if ok and inserted then return end
    end
    -- No chat box open: open one with the link, so shift-click always works
    -- (the real bank uses shift-click to split stacks instead).
    local open = ChatFrame_OpenChat or (ChatFrameUtil and ChatFrameUtil.OpenChat)
    if type(open) == "function" then pcall(open, link) end
end

local function slotOnClick(self)
    -- Plain clicks do nothing: the items are not really here.
    if not self.link then return end
    if type(IsShiftKeyDown) == "function" and IsShiftKeyDown() then
        linkInChat(self.link)
    elseif type(HandleModifiedItemClick) == "function" then
        pcall(HandleModifiedItemClick, self.link)
    end
end

-- Shared with the equipment view so every item button behaves the same.
PB.UI.ItemButton = {
    OnEnter = slotOnEnter,
    OnLeave = slotOnLeave,
    OnClick = slotOnClick,
    QualityColor = qualityColor,
    SetAtlas = setAtlas,
}

local function createSlot(parent, index)
    local slot = CreateFrame("Button", nil, parent)
    slot:SetSize(SLOT_SIZE, SLOT_SIZE)
    slot:RegisterForClicks("LeftButtonUp", "RightButtonUp")

    local bg = slot:CreateTexture(nil, "BACKGROUND")
    bg:SetAllPoints()
    slot.bg = bg

    local icon = slot:CreateTexture(nil, "BORDER")
    icon:SetAllPoints()
    slot.icon = icon

    local border = slot:CreateTexture(nil, "ARTWORK")
    border:SetAllPoints()
    setAtlas(border, "bank-frame-item-slotframe")

    local quality = slot:CreateTexture(nil, "OVERLAY")
    quality:SetAllPoints()
    quality:SetTexture(QUALITY_BORDER)
    quality:Hide()
    slot.quality = quality

    local count = slot:CreateFontString(nil, "OVERLAY", "NumberFontNormal")
    count:SetPoint("BOTTOMRIGHT", -2, 2)
    count:SetJustifyH("RIGHT")
    slot.count = count

    local highlight = slot:CreateTexture(nil, "HIGHLIGHT")
    highlight:SetAllPoints()
    highlight:SetTexture(SLOT_HIGHLIGHT)
    highlight:SetBlendMode("ADD")

    local column = (index - 1) % COLUMNS
    local row = math.floor((index - 1) / COLUMNS)
    slot:SetPoint("TOPLEFT", parent, "TOPLEFT",
        SLOT_LEFT + column * (SLOT_SIZE + SLOT_GAP_X),
        SLOT_TOP - row * ROW_STEP)

    slot:SetScript("OnEnter", slotOnEnter)
    slot:SetScript("OnLeave", slotOnLeave)
    slot:SetScript("OnClick", slotOnClick)
    return slot
end

local function fillSlot(slot, item)
    slot.link = item and item.link or nil
    if not item then
        slot.icon:SetTexture(nil)
        slot.count:SetText("")
        slot.quality:Hide()
        return
    end
    slot.icon:SetTexture(item.icon)
    slot.count:SetText((item.count or 1) > 1 and item.count or "")
    local r, g, b
    if (item.quality or 0) >= 2 then r, g, b = qualityColor(item.quality) end
    if r then
        slot.quality:SetVertexColor(r, g, b)
        slot.quality:Show()
    else
        slot.quality:Hide()
    end
end

-- Search -------------------------------------------------------------------

local function trim(text)
    if type(text) ~= "string" then return "" end
    return (string.gsub(text, "^%s*(.-)%s*$", "%1"))
end

-- Clearing from a tab, the dropdown or OnHide must not leave the window in
-- search mode, so the stored text goes first.
local function clearSearch()
    searchText = ""
    local box = frame and frame.searchBox
    if not box then return end
    pcall(box.SetText, box, "")
    if type(box.ClearFocus) == "function" then pcall(box.ClearFocus, box) end
end

local function createSearchBox()
    local ok, box = pcall(CreateFrame, "EditBox", FRAME_NAME .. "SearchBox", frame, "SearchBoxTemplate")
    if not ok or not box then
        ok, box = pcall(CreateFrame, "EditBox", FRAME_NAME .. "SearchBox", frame, "InputBoxTemplate")
    end
    if not ok or not box then return nil end
    box:SetSize(110, 20)
    box:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -56, -33)
    if type(box.SetAutoFocus) == "function" then pcall(box.SetAutoFocus, box, false) end
    -- The placeholder lives in the template's own font string, when it has one.
    pcall(function()
        if box.Instructions then box.Instructions:SetText(L.SEARCH) end
    end)
    local function onTextChanged(self)
        local gotText, text = pcall(self.GetText, self)
        searchText = trim(gotText and text or "")
        BankWindow:Refresh()
    end
    -- The template's own OnTextChanged drives the placeholder and the clear
    -- button, so ours is added beside it instead of replacing it.
    if type(box.HookScript) == "function" then
        pcall(box.HookScript, box, "OnTextChanged", onTextChanged)
    else
        box:SetScript("OnTextChanged", onTextChanged)
    end
    return box
end

-- Side tabs -------------------------------------------------------------

local function createSideTab(index, def)
    local tab = CreateFrame("Button", nil, frame)
    tab:SetSize(SIDE_TAB_SIZE, SIDE_TAB_SIZE)
    tab:SetPoint("TOPLEFT", frame, "TOPRIGHT", 0, -60 - (index - 1) * SIDE_TAB_STEP)
    tab.view = def

    local bg = tab:CreateTexture(nil, "BACKGROUND")
    bg:SetPoint("CENTER")
    if not setAtlas(bg, "common-sidetab", true) then bg:SetAllPoints() end

    local icon = tab:CreateTexture(nil, "ARTWORK")
    icon:SetSize(SIDE_TAB_SIZE - 20, SIDE_TAB_SIZE - 20)
    icon:SetPoint("CENTER", -2, 0)
    icon:SetTexture(def.icon)

    local selected = tab:CreateTexture(nil, "OVERLAY")
    selected:SetPoint("CENTER")
    setAtlas(selected, "common-sidetab-selected", true)
    tab.selected = selected

    local hover = tab:CreateTexture(nil, "HIGHLIGHT")
    hover:SetPoint("CENTER")
    setAtlas(hover, "common-sidetab-hover", true)

    tab:SetScript("OnEnter", function(self)
        if not GameTooltip then return end
        GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
        GameTooltip:SetText(L[def.label], 1, 1, 1)
        GameTooltip:Show()
    end)
    tab:SetScript("OnLeave", slotOnLeave)
    tab:SetScript("OnClick", function()
        view = def
        clearSearch()
        BankWindow:Refresh()
    end)
    return tab
end

-- Character selector -----------------------------------------------------

local function viewedKey()
    return charKey or (PB.DB and PB.DB.GetCharKey())
end

local function charLabel(char, key)
    local name = char.fullName or char.name or key
    local colors = RAID_CLASS_COLORS and char.class and RAID_CLASS_COLORS[char.class]
    if colors and colors.colorStr then return "|c" .. colors.colorStr .. name .. "|r" end
    return name
end

local function selectChar(key)
    charKey = key
    clearSearch()
    BankWindow:Refresh()
end

local function createSelector()
    -- WowStyle1DropdownTemplate is the dropdown the client itself uses (its
    -- atlases appear in the bank's tab settings); fall back to a button that
    -- cycles through the characters if this build lacks it.
    local ok, dropdown = pcall(CreateFrame, "DropdownButton", nil, frame, "WowStyle1DropdownTemplate")
    if ok and dropdown and type(dropdown.SetupMenu) == "function" then
        dropdown:SetWidth(190)
        dropdown:SetPoint("TOPLEFT", frame, "TOPLEFT", 70, -30)
        dropdown:SetupMenu(function(_, root)
            for _, entry in ipairs(PB.DB.ListChars()) do
                root:CreateRadio(charLabel(entry.char, entry.key),
                    function() return entry.key == viewedKey() end,
                    function() selectChar(entry.key) end)
            end
        end)
        return { dropdown = dropdown }
    end

    local button = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    button:SetSize(190, 22)
    button:SetPoint("TOPLEFT", frame, "TOPLEFT", 70, -30)
    button:SetScript("OnClick", function()
        local list = PB.DB.ListChars()
        if #list == 0 then return end
        local nextIndex = 1
        for i, entry in ipairs(list) do
            if entry.key == viewedKey() then nextIndex = i % #list + 1 end
        end
        selectChar(list[nextIndex].key)
    end)
    return { button = button }
end

local function updateSelector(char)
    local selector = frame.selector
    if not selector then return end
    local text = char and charLabel(char, viewedKey()) or ""
    if selector.dropdown then
        local dropdown = selector.dropdown
        if type(dropdown.GenerateMenu) == "function" then pcall(dropdown.GenerateMenu, dropdown) end
        if type(dropdown.OverrideText) == "function" then pcall(dropdown.OverrideText, dropdown, text) end
        dropdown:SetShown(#PB.DB.ListChars() > 0)
    else
        selector.button:SetText(text)
        selector.button:SetShown(#PB.DB.ListChars() > 1)
    end
end

-- Frame -------------------------------------------------------------------

-- The background and its corner shadows run down to the bottom edge, so the
-- money box sits on the same background instead of a separate strip.
local function addShadows(parent)
    local area = CreateFrame("Frame", nil, parent)
    area:SetAllPoints()
    local corners = {
        { "bank-frame-shadow-cornertopleft", "TOPLEFT" },
        { "bank-frame-shadow-cornertopright", "TOPRIGHT" },
        { "bank-frame-shadow-cornerbottomleft", "BOTTOMLEFT" },
        { "bank-frame-shadow-cornerbottomright", "BOTTOMRIGHT" },
    }
    for _, c in ipairs(corners) do
        local t = area:CreateTexture(nil, "BORDER")
        setAtlas(t, c[1], true)
        t:SetPoint(c[2])
    end
    return area
end

local function windowSettings()
    if type(PocketBankDB) ~= "table" then return nil end
    if type(PocketBankDB.settings) ~= "table" then PocketBankDB.settings = {} end
    return PocketBankDB.settings
end

-- The window grows downwards (bank bags, bags), so its top-left corner is
-- what gets saved and restored.
local function placeWindow()
    frame:ClearAllPoints()
    local settings = windowSettings()
    local saved = settings and settings.window
    if type(saved) == "table" and tonumber(saved.left) and tonumber(saved.top) then
        frame:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", saved.left, saved.top)
    else
        frame:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 16, -116)
    end
end

local function saveWindowPosition()
    local left, top = frame:GetLeft(), frame:GetTop()
    local settings = windowSettings()
    if settings and left and top then settings.window = { left = left, top = top } end
    placeWindow()
end

function BankWindow:ResetPosition()
    local settings = windowSettings()
    if settings then settings.window = nil end
    if frame then placeWindow() end
end

local function create()
    local ok, created = pcall(CreateFrame, "Frame", FRAME_NAME, UIParent, "PortraitFrameTemplate")
    if not ok or not created then return nil end
    frame = created
    frame:SetSize(WIDTH, HEIGHT)
    placeWindow()
    frame:SetFrameStrata("MEDIUM")
    frame:SetToplevel(true)
    frame:EnableMouse(true)
    frame:SetMovable(true)
    frame:SetClampedToScreen(true)
    frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", function(self) self:StartMoving() end)
    frame:SetScript("OnDragStop", function(self)
        self:StopMovingOrSizing()
        -- The position lives in PocketBankDB, not in the client's layout cache.
        if type(self.SetUserPlaced) == "function" then pcall(self.SetUserPlaced, self, false) end
        saveWindowPosition()
    end)
    frame:Hide()
    if not (type(frame.HookScript) == "function" and pcall(frame.HookScript, frame, "OnHide", clearSearch)) then
        frame:SetScript("OnHide", clearSearch)
    end

    -- PortraitFrameTemplate brings the metal border, portrait, title and
    -- close button; the rock background and streaks are the bank's own.
    local rock = frame:CreateTexture(nil, "BACKGROUND", nil, -2)
    rock:SetTexture(ROCK_BACKGROUND, "REPEAT", "REPEAT")
    rock:SetHorizTile(true)
    rock:SetVertTile(true)
    rock:SetPoint("TOPLEFT", 2, -21)
    rock:SetPoint("BOTTOMRIGHT", -2, 2)

    local background = frame:CreateTexture(nil, "BACKGROUND", nil, -1)
    setAtlas(background, "bank-frame-background")
    background:SetPoint("TOPLEFT", 0, -20)
    background:SetPoint("BOTTOMRIGHT", 0, 0)

    local streaks = frame:CreateTexture(nil, "BORDER")
    setAtlas(streaks, "_UI-Frame-TopTileStreaks")
    streaks:SetPoint("TOPLEFT", 4, -21)
    streaks:SetPoint("TOPRIGHT", -4, -21)
    streaks:SetHeight(43)

    local shadows = addShadows(frame)

    frame.sideTabs = {}
    for index, def in ipairs(VIEWS) do frame.sideTabs[index] = createSideTab(index, def) end
    frame.selector = createSelector()
    frame.searchBox = createSearchBox()

    local divider = frame:CreateTexture(nil, "ARTWORK")
    setAtlas(divider, "bank-divider")
    divider:SetHeight(16)
    frame.divider = divider

    local scanned = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    scanned:SetPoint("TOPLEFT", divider, "BOTTOMLEFT", 8, -10)
    scanned:SetJustifyH("LEFT")
    frame.scanned = scanned

    -- The slots are child frames, so the message needs a frame above them.
    local notice = CreateFrame("Frame", nil, frame)
    notice:SetFrameLevel(frame:GetFrameLevel() + 5)
    notice:SetSize(WIDTH - 80, 60)
    notice:SetPoint("CENTER", frame, "TOPLEFT", WIDTH / 2, SLOT_TOP - ROWS * ROW_STEP / 2)
    local shade = notice:CreateTexture(nil, "BACKGROUND")
    shade:SetAllPoints()
    shade:SetColorTexture(0, 0, 0, 0.75)
    local empty = notice:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
    empty:SetPoint("CENTER")
    empty:SetWidth(WIDTH - 120)
    frame.empty = empty
    frame.notice = notice

    -- The template's border is a child frame drawn over the parent's own
    -- regions, so the money box needs a frame of its own above it.
    local footer = CreateFrame("Frame", nil, frame)
    footer:SetFrameLevel(frame:GetFrameLevel() + 10)
    footer:SetSize(180, 25)
    footer:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -3, 3)
    local okEdge, edge = pcall(CreateFrame, "Frame", nil, footer, "ThinGoldEdgeTemplate")
    if okEdge and edge then
        edge:SetSize(178, 19)
        edge:SetPoint("LEFT", footer, "LEFT", 0, 0)
    end
    local okMoney, moneyFrame = pcall(CreateFrame, "Frame", FRAME_NAME .. "Money", footer, "SmallMoneyFrameTemplate")
    if okMoney and moneyFrame and type(MoneyFrame_Update) == "function" then
        moneyFrame:SetPoint("RIGHT", footer, "RIGHT", 0, 0)
        -- STATIC: show the saved amount, not the live money of whoever is logged in.
        if type(MoneyFrame_SetType) == "function" then pcall(MoneyFrame_SetType, moneyFrame, "STATIC") end
        frame.moneyFrame = moneyFrame
    else
        local money = footer:CreateFontString(nil, "OVERLAY", "NumberFontNormalRight")
        money:SetPoint("RIGHT", footer, "RIGHT", -8, 0)
        frame.money = money
    end

    -- Everything the bank and bags grid owns, hidden in the equipment view.
    frame.gridParts = { rock, background, streaks, shadows, divider, scanned, footer }
    frame.footer = footer

    if type(UISpecialFrames) == "table" then UISpecialFrames[#UISpecialFrames + 1] = FRAME_NAME end
    return frame
end

local function setTitle(text)
    if type(frame.SetTitle) == "function" and pcall(frame.SetTitle, frame, text) then return end
    local title = frame.TitleText or (frame.TitleContainer and frame.TitleContainer.TitleText)
    if title then title:SetText(text) end
end

local function setPortrait(char)
    local isPlayer = char and PB.DB and char.guid == PB.DB.GetCharKey()
    if isPlayer and type(frame.SetPortraitToUnit) == "function" and pcall(frame.SetPortraitToUnit, frame, "player") then
        return
    end
    local texture = frame.portrait or (frame.PortraitContainer and frame.PortraitContainer.portrait)
    if isPlayer and texture and type(SetPortraitTexture) == "function" and pcall(SetPortraitTexture, texture, "player") then
        return
    end
    -- Other characters cannot be rendered offline: use their class icon.
    if char and char.class and type(frame.SetPortraitToClassIcon) == "function"
        and pcall(frame.SetPortraitToClassIcon, frame, char.class) then
        return
    end
    local asset = "Interface\\AddOns\\" .. ADDON .. "\\Media\\logo"
    if type(frame.SetPortraitToAsset) == "function" then pcall(frame.SetPortraitToAsset, frame, asset) end
end

-- The client shows the main bank and every bank bag as one grid, bags
-- appended after the 48 main slots, and grows the window a row at a time.
local function flatten(tabs)
    local items, total = {}, 0
    for _, tab in ipairs(tabs) do
        local tabItems = tab.items or {}
        for slot = 1, tab.size or 0 do
            total = total + 1
            items[total] = tabItems[slot]
        end
    end
    return items, total
end

local function layout(total, atlas)
    local rows = math.max(ROWS, math.ceil(total / COLUMNS))
    frame:SetHeight(HEIGHT + (rows - ROWS) * ROW_STEP)
    local y = SLOT_TOP - rows * ROW_STEP + 1
    frame.divider:ClearAllPoints()
    frame.divider:SetPoint("TOPLEFT", frame, "TOPLEFT", 32, y)
    frame.divider:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -35, y)
    -- Before the first visit there is nothing saved: show the empty 8x6 grid.
    local shown = total > 0 and total or COLUMNS * ROWS
    for i = #slots + 1, shown do slots[i] = createSlot(frame, i) end
    for i, slot in ipairs(slots) do
        slot:SetShown(i <= shown)
        setAtlas(slot.bg, atlas or view.slotAtlas)
    end
end

function BankWindow:Refresh()
    if not frame then return end
    local char = currentChar()
    local isPlayer = viewedKey() == (PB.DB and PB.DB.GetCharKey())
    -- A character search takes over the grid while it has text.
    local searching = searchText ~= "" and not view.paperdoll
    setPortrait(char)
    updateSelector(char)
    for _, tab in ipairs(frame.sideTabs) do
        tab.selected:SetShown(not searching and tab.view == view)
    end

    local equipmentView = PB.UI.EquipmentView
    local paperdoll = view.paperdoll and equipmentView ~= nil
    for _, part in ipairs(frame.gridParts) do part:SetShown(not paperdoll) end
    if frame.searchBox then frame.searchBox:SetShown(not paperdoll) end
    if paperdoll then
        for _, slot in ipairs(slots) do slot:Hide() end
        frame.notice:Hide()
        frame:SetSize(equipmentView.WIDTH, equipmentView.HEIGHT)
        setTitle(char and (char.fullName or char.name) or L[view.label])
        equipmentView:Show(frame, char, isPlayer)
        return
    end
    if equipmentView then equipmentView:Hide() end
    frame:SetWidth(WIDTH)

    if searching and PB.Search then
        local results, total = PB.Search.Find(searchText)
        setTitle(L.SEARCH_TITLE)
        layout(#results, SEARCH_SLOT_ATLAS)
        for i, slot in ipairs(slots) do fillSlot(slot, results[i]) end
        frame.notice:SetShown(total == 0)
        if total == 0 then
            frame.empty:SetText(string.format(L.SEARCH_NONE, searchText))
            frame.scanned:SetText("")
        else
            frame.empty:SetText("")
            if total > #results then
                frame.scanned:SetText(string.format(L.SEARCH_MORE, #results, total))
            else
                frame.scanned:SetText(string.format(L.SEARCH_RESULTS, total))
            end
        end
        -- The money box belongs to one character: an empty box looks broken.
        frame.footer:Hide()
        return
    end

    local section = char and char[view.key]
    local tabs = section and section.tabs or {}
    setTitle(char and char.name and string.format(L[view.title], char.name) or L[view.label])

    local items, total = flatten(tabs)
    layout(total)
    for i, slot in ipairs(slots) do fillSlot(slot, items[i]) end

    frame.notice:SetShown(total == 0)
    if total > 0 then
        frame.empty:SetText("")
        frame.scanned:SetText(string.format(L.LAST_SCANNED, date(L.DATE_FORMAT, section.scanned or 0)))
    else
        frame.empty:SetText(isPlayer and L[view.empty] or L[view.emptyOther])
        frame.scanned:SetText("")
    end

    local amount = char and char.money
    if frame.moneyFrame then
        frame.moneyFrame:SetShown(amount ~= nil)
        if amount then pcall(MoneyFrame_Update, frame.moneyFrame, amount, true) end
    elseif amount and type(GetCoinTextureString) == "function" then
        frame.money:SetText(GetCoinTextureString(amount))
    else
        frame.money:SetText("")
    end
end

function BankWindow:Show(key)
    if not frame and not create() then
        print(L.WINDOW_NOT_READY)
        return
    end
    charKey = key
    self:Refresh()
    frame:Show()
end

function BankWindow:Hide()
    if frame then frame:Hide() end
end

function BankWindow:Toggle()
    if frame and frame:IsShown() then
        self:Hide()
    else
        self:Show(charKey)
    end
end

local function refreshIfShown()
    if frame and frame:IsShown() then BankWindow:Refresh() end
end
PB.RegisterCallback("BANK_SCANNED", refreshIfShown)
PB.RegisterCallback("BAGS_SCANNED", refreshIfShown)
PB.RegisterCallback("EQUIPMENT_SCANNED", refreshIfShown)
PB.RegisterCallback("CHAR_DELETED", function(key)
    -- The deleted character cannot stay on screen, so the window returns to
    -- the logged-in one, as selecting a character does.
    if charKey ~= nil and key == charKey then
        charKey = nil
        clearSearch()
    end
    refreshIfShown()
end)
