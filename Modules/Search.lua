local ADDON, PB = ...

local Search = {}
PB.Search = Search

-- The window grid holds ten rows of eight; more matches only change the counter.
local MAX_RESULTS = 80

local function trim(text)
    if type(text) ~= "string" then return "" end
    return (string.gsub(text, "^%s*(.-)%s*$", "%1"))
end

local function itemName(link)
    if type(link) ~= "string" then return nil end
    return string.match(link, "%[(.-)%]")
end

local function addItem(items, item, amount)
    local entry = items[item.id]
    if not entry then
        entry = { id = item.id, count = 0 }
        items[item.id] = entry
    end
    -- A gear slot may lack the link or icon that a bank slot of the same item has.
    if not entry.link and item.link then
        entry.link = item.link
        entry.name = itemName(item.link)
    end
    if not entry.icon and item.icon then entry.icon = item.icon end
    if entry.quality == nil and item.quality ~= nil then entry.quality = item.quality end
    entry.count = entry.count + amount
end

local function addTabs(items, container)
    if type(container) ~= "table" or type(container.tabs) ~= "table" then return end
    for _, tab in ipairs(container.tabs) do
        if type(tab) == "table" and type(tab.items) == "table" then
            for _, item in pairs(tab.items) do
                if type(item) == "table" and item.id then
                    addItem(items, item, tonumber(item.count) or 1)
                end
            end
        end
    end
end

-- Equipped items carry no stack count: one item per occupied slot.
local function addEquipped(items, container)
    if type(container) ~= "table" or type(container.slots) ~= "table" then return end
    for _, item in pairs(container.slots) do
        if type(item) == "table" and item.id then addItem(items, item, 1) end
    end
end

local function collect()
    local items = {}
    if not (PB.DB and PB.DB.ListChars) then return items end
    for _, entry in ipairs(PB.DB.ListChars()) do
        local char = entry.char
        if type(char) == "table" then
            addTabs(items, char.bank)
            addTabs(items, char.bags)
            addEquipped(items, char.equipment)
        end
    end
    return items
end

local function before(a, b)
    local qa, qb = a.quality or 0, b.quality or 0
    if qa ~= qb then return qa > qb end
    if a.name ~= b.name then return (a.name or "") < (b.name or "") end
    return a.id < b.id
end

-- Results are { id, link, icon, quality, count, name }, at most MAX_RESULTS of
-- them, plus how many items match in the whole account.
function Search.Find(text)
    text = trim(text)
    if text == "" then return {}, 0 end
    local needle = string.lower(text)
    local matches = {}
    for _, item in pairs(collect()) do
        if item.name and string.find(string.lower(item.name), needle, 1, true) then
            matches[#matches + 1] = item
        end
    end
    table.sort(matches, before)
    local total = #matches
    for i = #matches, MAX_RESULTS + 1, -1 do matches[i] = nil end
    return matches, total
end
