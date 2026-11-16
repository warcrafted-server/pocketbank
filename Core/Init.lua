local ADDON, PB = ...

PB.name = ADDON

local function metadata(field)
    local get = (C_AddOns and C_AddOns.GetAddOnMetadata) or GetAddOnMetadata
    return get and get(ADDON, field)
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("ADDON_LOADED")
frame:SetScript("OnEvent", function(_, _, name)
    if name ~= ADDON then return end
    PocketBankDB = PocketBankDB or { schemaVersion = 1, chars = {} }
    frame:UnregisterEvent("ADDON_LOADED")
end)

SLASH_POCKETBANK1 = "/pocketbank"
SLASH_POCKETBANK2 = "/pb"
SlashCmdList["POCKETBANK"] = function(msg)
    local cmd = strlower(strtrim(msg or ""))
    if cmd == "debug" and PB.Debug then
        PB.Debug.Run()
    else
        print("PocketBank " .. (metadata("Version") or "?"))
    end
end
