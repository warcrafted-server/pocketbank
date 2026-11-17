local ADDON, PB = ...

local Tooltip = {}
PB.Tooltip = Tooltip

-- itemID -> { { key, char, bank, bags, equipped, total }, ... } in ListChars
-- order, built on first use because a scan can change any character.
local index

local function countItem(counts, id, key, amount)
    local entry = counts[id]
    if not entry then
        entry = { bank = 0, bags = 0, equipped = 0 }
        counts[id] = entry
    end
    entry[key] = entry[key] + amount
end

local function countTabs(char, field, key, counts)
    local container = char[field]
    if type(container) ~= "table" or type(container.tabs) ~= "table" then return end
    for _, tab in ipairs(container.tabs) do
        if type(tab.items) == "table" then
            for _, item in pairs(tab.items) do
                if item.id then countItem(counts, item.id, key, tonumber(item.count) or 1) end
            end
        end
    end
end

-- Equipped items carry no stack count: one item per occupied slot.
local function countEquipped(char, counts)
    local container = char.equipment
    if type(container) ~= "table" or type(container.slots) ~= "table" then return end
    for _, item in pairs(container.slots) do
        if item.id then countItem(counts, item.id, "equipped", 1) end
    end
end

local function buildIndex()
    local built = {}
    if not (PB.DB and PB.DB.ListChars) then return built end
    for _, entry in ipairs(PB.DB.ListChars()) do
        local char = entry.char
        local counts = {}
        countTabs(char, "bank", "bank", counts)
        countTabs(char, "bags", "bags", counts)
        countEquipped(char, counts)
        for id, parts in pairs(counts) do
            local total = parts.bank + parts.bags + parts.equipped
            if total > 0 then
                local list = built[id]
                if not list then
                    list = {}
                    built[id] = list
                end
                list[#list + 1] = {
                    key = entry.key, char = char,
                    bank = parts.bank, bags = parts.bags, equipped = parts.equipped, total = total,
                }
            end
        end
    end
    return built
end

function Tooltip.GetCounts(itemID)
    if not itemID then return {} end
    if not index then index = buildIndex() end
    return index[itemID] or {}
end

local function invalidate()
    index = nil
end

PB.RegisterCallback("BANK_SCANNED", invalidate)
PB.RegisterCallback("BAGS_SCANNED", invalidate)
PB.RegisterCallback("EQUIPMENT_SCANNED", invalidate)

local function classColoredName(char, key)
    local name = char.fullName or char.name or key
    local color = char.class and RAID_CLASS_COLORS and RAID_CLASS_COLORS[char.class]
    if color and color.colorStr then return "|c" .. color.colorStr .. name .. "|r" end
    return name
end

local function countsText(entry)
    local L = PB.L
    local parts = {}
    if entry.bank > 0 then parts[#parts + 1] = L.BANK .. ": " .. entry.bank end
    if entry.bags > 0 then parts[#parts + 1] = L.BAGS .. ": " .. entry.bags end
    if entry.equipped > 0 then parts[#parts + 1] = L.EQUIPPED .. ": " .. entry.equipped end
    return entry.total .. " (" .. table.concat(parts, ", ") .. ")"
end

local function isShoppingTooltip(tooltip)
    if type(tooltip.GetName) ~= "function" then return false end
    local ok, name = pcall(tooltip.GetName, tooltip)
    return ok and type(name) == "string" and string.find(name, "^ShoppingTooltip") ~= nil
end

local function appendLines(tooltip, itemID)
    if not itemID or isShoppingTooltip(tooltip) then return end
    local db = PocketBankDB
    if type(db) == "table" and type(db.settings) == "table" and db.settings.tooltip == false then
        return
    end
    if type(tooltip.AddDoubleLine) ~= "function" then return end
    local counts = Tooltip.GetCounts(itemID)
    if #counts == 0 then return end
    local total = 0
    for _, entry in ipairs(counts) do
        tooltip:AddDoubleLine(classColoredName(entry.char, entry.key), countsText(entry), 1, 1, 1, 1, 1, 1)
        total = total + entry.total
    end
    if #counts > 1 then
        tooltip:AddDoubleLine(PB.L.TOTAL, tostring(total), 1, 0.82, 0, 1, 1, 1)
    end
    -- The client re-lays out the tooltip only when it is shown again.
    tooltip:Show()
end

local function registerDataProcessor()
    if not TooltipDataProcessor or not TooltipDataProcessor.AddTooltipPostCall then return false end
    local itemType = Enum and Enum.TooltipDataType and Enum.TooltipDataType.Item
    if not itemType then return false end
    return pcall(TooltipDataProcessor.AddTooltipPostCall, itemType, function(tooltip, data)
        pcall(appendLines, tooltip, data and data.id)
    end)
end

local function hookSetItem(tooltip)
    if not tooltip or type(tooltip.HookScript) ~= "function" then return end
    pcall(tooltip.HookScript, tooltip, "OnTooltipSetItem", function(self)
        local ok, _, link = pcall(self.GetItem, self)
        if not ok or type(link) ~= "string" then return end
        pcall(appendLines, self, tonumber(string.match(link, "item:(%d+)")))
    end)
end

-- The client's tooltip system is not verified yet: prefer the modern hook and
-- fall back to the script when the client does not expose it.
if not registerDataProcessor() then
    hookSetItem(GameTooltip)
    hookSetItem(ItemRefTooltip)
end
