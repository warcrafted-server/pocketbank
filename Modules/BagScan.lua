local ADDON, PB = ...

local BagScan = {}
PB.BagScan = BagScan

local ENTER_DELAY = 1
local CHANGE_DELAY = 0.5

local CONTAINERS = { "Backpack", "Bag_1", "Bag_2", "Bag_3", "Bag_4", "ReagentBag" }

local scanScheduled = false

local function containerIDs()
    local ids = {}
    for index, name in ipairs(CONTAINERS) do
        local id = Enum and Enum.BagIndex and Enum.BagIndex[name]
        ids[index] = id or (index - 1)
    end
    return ids
end

local function readContents()
    local tabs = {}
    for index, id in ipairs(containerIDs()) do
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
                end
            end
        end
        tabs[index] = {
            id = id,
            size = size,
            items = items,
        }
    end
    return tabs
end

function BagScan.Scan()
    local char = PB.DB and PB.DB.GetChar(true)
    if not char then return end

    char.bags = { scanned = time(), tabs = readContents() }

    PB.FireCallback("BAGS_SCANNED", char)
    return char.bags
end

local function schedule(delay)
    if scanScheduled then return end
    scanScheduled = true
    C_Timer.After(delay, function()
        scanScheduled = false
        BagScan.Scan()
    end)
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_ENTERING_WORLD")
frame:RegisterEvent("BAG_UPDATE_DELAYED")
frame:SetScript("OnEvent", function(_, event)
    -- Bag contents may still be empty right after entering the world.
    if event == "PLAYER_ENTERING_WORLD" then
        schedule(ENTER_DELAY)
    else
        schedule(CHANGE_DELAY)
    end
end)
