# PocketBank

[Español](README.md)

Addon for **WoW Forever** (Interface 16001) that shows the contents of your bank, bags and equipment, including those of the other characters on your account, without visiting the bank. A modern alternative to BankItems, which is no longer supported.

> **Status:** version 0.2.0. It shows the bank of every character that has visited it; bags, equipment and the rest arrive in the next versions.

![PocketBank window](docs/img/capturas/PocketBank-0.2.0-personajes.png)

## Requirements

- WoW Forever (`_forever_` client, Interface 16001).

## Installation

From the CurseForge app (select your Forever installation) or at https://www.curseforge.com/wow/addons/pocketbank. Manually: copy the `PocketBank` folder into `World of Warcraft\_forever_\Interface\AddOns\` and restart the game.

## Usage

1. Visit the bank once: PocketBank saves its contents and says so in the chat ("Bank saved (N items)"). It saves again every time you open it.
2. From anywhere, click the minimap button or type `/pb` to open or close the bank window. `Esc` also closes it.
3. To see another character's bank, pick it in the dropdown at the top of the window. Each character must have visited the bank once.
4. Hover an item to see its tooltip; Shift + click links it in chat.

The minimap button can be dragged around the minimap and remembers its position.

| Command | What it does |
|---|---|
| `/pb` or `/pocketbank` | Opens or closes the bank window |
| `/pb version` | Shows the version |
| `/pb debug`, `/pb frames` | Diagnostics for support (saved on `/reload`) |

## Credits and license

**PocketBank** is developed and maintained by **WarCrafted**.
Copyright (C) 2026 WarCrafted.

Licensed under [WNCL-1.0](LICENSE): free to use, study, modify and share for non-commercial purposes. Selling or any commercial use requires written permission.

Copies and forks must keep this attribution and link to https://github.com/warcrafted-server/pocketbank.

### Third-party material

This project contains no third-party material.

Web: https://portal.warcrafted.com/
