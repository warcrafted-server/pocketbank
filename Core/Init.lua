local ADDON, PB = ...

PB.name = ADDON

local callbacks = {}

function PB.RegisterCallback(name, fn)
    if type(name) ~= "string" or type(fn) ~= "function" then return end
    local list = callbacks[name]
    if not list then
        list = {}
        callbacks[name] = list
    end
    list[#list + 1] = fn
end

function PB.FireCallback(name, ...)
    local list = callbacks[name]
    if not list then return end
    for i = 1, #list do list[i](...) end
end

function PB.ToggleWindow()
    if PB.UI and PB.UI.BankWindow then
        PB.UI.BankWindow:Toggle()
    else
        print(PB.L.WINDOW_NOT_READY)
    end
end

local function metadata(field)
    local get = (C_AddOns and C_AddOns.GetAddOnMetadata) or GetAddOnMetadata
    return get and get(ADDON, field)
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("ADDON_LOADED")
frame:RegisterEvent("PLAYER_LOGIN")
frame:RegisterEvent("PLAYER_ENTERING_WORLD")
frame:RegisterEvent("PLAYER_MONEY")
frame:RegisterEvent("PLAYER_LOGOUT")
frame:SetScript("OnEvent", function(_, event, name)
    if event == "ADDON_LOADED" then
        if name ~= ADDON then return end
        if PB.DB then PB.DB.Init() end
        frame:UnregisterEvent("ADDON_LOADED")
    elseif PB.DB then
        PB.DB.SaveCharMeta(event)
    end
end)

SLASH_POCKETBANK1 = "/pocketbank"
SLASH_POCKETBANK2 = "/pb"
SlashCmdList["POCKETBANK"] = function(msg)
    local cmd = strlower(strtrim(msg or ""))
    if cmd == "debug" and PB.Debug then
        PB.Debug.Run()
    elseif cmd == "frames" and PB.Debug then
        PB.Debug.Frames()
    elseif cmd == "paperdoll" and PB.Debug then
        PB.Debug.Paperdoll()
    elseif cmd:match("^modeltest") and PB.Debug then
        PB.Debug.ModelTest(strtrim(cmd:sub(10)))
    elseif cmd == "" then
        PB.ToggleWindow()
    else
        print("PocketBank " .. (metadata("Version") or "?"))
    end
end
