local ADDON, PB = ...

local BankScan = {}
PB.BankScan = BankScan

local OPEN_DELAY = 0.3
local CHANGE_DELAY = 0.5

local bankOpen = false
local scanScheduled = false
local announceScan = false

local function tabIDs()
    if C_Bank and C_Bank.FetchPurchasedBankTabIDs and Enum and Enum.BankType then
        local ok, ids = pcall(C_Bank.FetchPurchasedBankTabIDs, Enum.BankType.Character)
        if ok and type(ids) == "table" and #ids > 0 then return ids end
    end
    local ids = {}
    for i = 1, 9 do
        local id = Enum and Enum.BagIndex and Enum.BagIndex["CharacterBankTab_" .. i]
        if id then ids[#ids + 1] = id end
    end
    return ids
end

local function tabInfo()
    local byID = {}
    if C_Bank and C_Bank.FetchPurchasedBankTabData and Enum and Enum.BankType then
        local ok, data = pcall(C_Bank.FetchPurchasedBankTabData, Enum.BankType.Character)
        if ok and type(data) == "table" then
            for _, info in ipairs(data) do
                if type(info) == "table" and info.ID ~= nil then byID[info.ID] = info end
            end
        end
    end
    return byID
end

local function readContents()
    local infoByID = tabInfo()
    local tabs = {}
    local count = 0
    for index, id in ipairs(tabIDs()) do
        local size = 0
        if C_Container and C_Container.GetContainerNumSlots then
            local ok, slots = pcall(C_Container.GetContainerNumSlots, id)
            if ok and type(slots) == "number" then size = slots end
        end
        local items = {}
        if size > 0 and C_Container and C_Container.GetContainerItemInfo then
            for slot = 1, size do
                local ok, item = pcall(C_Container.GetContainerItemInfo, id, slot)
                if ok and type(item) == "table" and item.itemID then
                    items[slot] = {
                        id = item.itemID,
                        count = item.stackCount,
                        link = item.hyperlink,
                        icon = item.iconFileID,
                        quality = item.quality,
                    }
                    count = count + 1
                end
            end
        end
        local info = infoByID[id] or {}
        tabs[index] = {
            id = id,
            name = info.name,
            icon = info.icon,
            size = size,
            items = items,
        }
    end
    return tabs, count
end

function BankScan.Scan()
    local char = PB.DB and PB.DB.GetChar(true)
    if not char then return end

    local tabs, count = readContents()
    char.bank = { scanned = time(), tabs = tabs }

    if announceScan then
        announceScan = false
        local message = PB.L and PB.L.BANK_SAVED
        if message then print(string.format(message, count)) end
    end

    PB.FireCallback("BANK_SCANNED", char)
    return char.bank
end

local function schedule(delay)
    if scanScheduled then return end
    scanScheduled = true
    C_Timer.After(delay, function()
        scanScheduled = false
        if bankOpen then BankScan.Scan() end
    end)
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("BANKFRAME_OPENED")
frame:RegisterEvent("BANKFRAME_CLOSED")
frame:RegisterEvent("PLAYERBANKSLOTS_CHANGED")
frame:RegisterEvent("BAG_UPDATE_DELAYED")
frame:SetScript("OnEvent", function(_, event)
    if event == "BANKFRAME_OPENED" then
        bankOpen = true
        announceScan = true
        schedule(OPEN_DELAY)
    elseif event == "BANKFRAME_CLOSED" then
        bankOpen = false
    elseif bankOpen then
        schedule(CHANGE_DELAY)
    end
end)
