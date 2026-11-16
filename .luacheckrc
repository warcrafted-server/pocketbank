std = "lua51"
max_line_length = false
ignore = { "211/ADDON" }

globals = {
    "PocketBankDB",
    "SLASH_POCKETBANK1",
    "SLASH_POCKETBANK2",
    "SlashCmdList",
}

read_globals = {
    "C_AddOns",
    "C_Bank",
    "C_Container",
    "C_Timer",
    "CreateFrame",
    "GameTooltip",
    "Minimap",
    "GetAddOnMetadata",
    "GetLocale",
    "UIParent",
    "BankFrame",
    "Enum",
    "GetBuildInfo",
    "GetCursorPosition",
    "GetMoney",
    "GetRealmName",
    "UnitClass",
    "UnitFactionGroup",
    "UnitLevel",
    "UnitName",
    "time",
    "date",
    "strjoin",
    "strlower",
    "strtrim",
    "tostringall",
    "print",
}

exclude_files = {
    ".agentrelay/",
    ".agents/",
}
