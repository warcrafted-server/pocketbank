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
    "C_Container",
    "CreateFrame",
    "GetAddOnMetadata",
    "GetLocale",
    "UIParent",
    "BankFrame",
    "Enum",
    "GetBuildInfo",
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
