local ADDON, PB = ...

local EquipScan = {}
PB.EquipScan = EquipScan

local ENTER_DELAY = 1
local CHANGE_DELAY = 0.5

-- Slot 0 holds ammo and slot 18 the ranged item in older clients, and this
-- client may not have every slot in 0..19: empty or failing slots are normal.
local FIRST_SLOT = 0
local LAST_SLOT = 19

local scanScheduled = false

local function readSlots()
    local slots = {}
    for slot = FIRST_SLOT, LAST_SLOT do
        local okLink, link = pcall(GetInventoryItemLink, "player", slot)
        if not okLink then link = nil end
        local okID, id = pcall(GetInventoryItemID, "player", slot)
        if not okID then id = nil end
        if link or id then
            if not id and link then
                id = tonumber(string.match(link, "item:(%d+)"))
            end
            if id then
                local okIcon, icon = pcall(GetInventoryItemTexture, "player", slot)
                local okQuality, quality = pcall(GetInventoryItemQuality, "player", slot)
                if not okIcon then icon = nil end
                if not okQuality then quality = nil end
                slots[slot] = {
                    id = id,
                    link = link,
                    icon = icon,
                    quality = quality,
                }
            end
        end
    end
    return slots
end

function EquipScan.Scan()
    local char = PB.DB and PB.DB.GetChar(true)
    if not char then return end

    char.equipment = { scanned = time(), slots = readSlots() }

    PB.FireCallback("EQUIPMENT_SCANNED", char)
    return char.equipment
end

local function schedule(delay)
    if scanScheduled then return end
    scanScheduled = true
    C_Timer.After(delay, function()
        scanScheduled = false
        EquipScan.Scan()
    end)
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_ENTERING_WORLD")
frame:RegisterEvent("PLAYER_EQUIPMENT_CHANGED")
frame:SetScript("OnEvent", function(_, event)
    -- Equipment may still be empty right after entering the world.
    if event == "PLAYER_ENTERING_WORLD" then
        schedule(ENTER_DELAY)
    else
        schedule(CHANGE_DELAY)
    end
end)
