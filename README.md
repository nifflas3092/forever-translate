# Forever Translate

Read and answer World of Warcraft: Forever chat in any language.

**Get the addon on [CurseForge](https://www.curseforge.com/wow/addons/forever-translate)** ·
**Download the Windows app from [Releases](../../releases)** ·
**[Watch it in action](https://www.youtube.com/shorts/JIp8bgGzddc)**

Forever Translate has two parts:

- **The addon** (on CurseForge). On its own, it adds short grey English hints
  after common foreign WoW words in chat, for example
  `alguien para dg? falta tanque (EN: anyone, dungeon, need, tank)`.
  It also passes chat to the desktop app.
- **The desktop app** (this repository's Releases page, Windows). It
  translates every foreign message in full, shows it in a window styled like
  the in-game chat frame, and translates your replies into the other
  player's language.

WoW addons can't use the internet, so the addon shows each message as a small
strip of coloured squares in a corner of the game window, and the app reads
that strip from the screen. The app never touches the game's files or memory,
and never types or clicks in the game.

## Install

1. Install the **Forever Translate** addon from
   [CurseForge](https://www.curseforge.com/wow/addons/forever-translate), or copy
   `addon/ForeverTranslate` into
   `World of Warcraft\_forever_\Interface\AddOns\`.
2. Download `ForeverTranslate.exe` from the latest
   [release](../../releases). Put it in its own folder, since it saves its
   settings (`config.json`) next to itself.
3. Run WoW in **Windowed** or **Windowed (Fullscreen)** mode, start the app
   and log in. The app shows **Connected** within a second or two.

The app isn't code-signed, so Windows may show "Windows protected your PC".
Click **More info** and then **Run anyway**. Every release lists SHA-256
checksums (`SHA256SUMS.txt`), and the `.exe` is built from this source code by
GitHub's own servers (see `.github/workflows/build.yml`).

## Use

- **Tabs** (All, Party, Guild, Whispers, World) filter the chat. A dot marks
  a tab with new messages.
- **Reply:** type in your own language and press Enter. The app translates
  it into the language shown at the left of the reply bar (it follows
  whoever spoke last; click it to choose another), copies it, and switches
  you to WoW. Then press **Enter, Ctrl+V, Enter**.
- Your language is taken from your WoW client's language automatically.

### In-game commands

| Command | What it does |
|---|---|
| `/ftr` | Show the commands |
| `/ftr on` / `/ftr off` | Turn sending to the app on or off (off also hides the strip) |
| `/ftr gloss` | Turn the grey English slang hints on or off |
| `/ftr move` | Unlock the strip so you can drag it; type it again to lock it |
| `/ftr reset` | Put the strip back in the bottom-left corner |
| `/ftr channel <name>` | Turn a chat type on or off: say, yell, whisper, party, raid, guild, officer, instance, channel |
| `/ftr test` | Send 3 sample messages to the app |

## Settings (`config.json`, next to the app)

| Setting | Meaning |
|---|---|
| `engine` | `"mymemory"` (free, default), `"deepl"`, `"claude"` or `"google"` |
| `mymemory_email` | Optional. Your email raises MyMemory's free limit from 5,000 to 50,000 characters a day |
| `deepl_key` | Your DeepL API key (the free plan gives 500,000 characters a month) |
| `claude_key`, `claude_model` | Your Anthropic API key; best with WoW slang, small cost per message |
| `my_language` | `"auto"` (your WoW client's language), or a code like `"en"` or `"fr"` |
| `show_original` | Also show the original message under the translation |
| `show_english_messages` | Also list messages that didn't need translating |
| `jump_to_wow` | Switch to WoW after a reply is copied |
| `always_on_top`, `opacity`, `font_size` | How the window looks |

`"google"` uses Google Translate's unofficial public endpoint. It works well,
but it isn't an official Google service and may stop working at any time.

## Privacy

- **No accounts, ads, analytics or tracking.** The app never contacts the
  author or any server of ours.
- **Chat goes only to the translation service you pick** (MyMemory by
  default), and only messages that need translating. Read that service's
  privacy policy if this matters to you.
- **Your API keys and email stay in `config.json` on your PC.** They're only
  sent to the service they belong to. Don't share that file.
- **The app keeps no chat history on disk.** Closing it clears the window.
  The only other file it writes is `forever_translate.log`, which holds error
  messages, never chat.
- **For streamers:** the strip on screen contains the chat it's sending,
  including whispers, and someone could decode it from a recording. Use
  `/ftr off` while streaming, or `/ftr channel whisper` to leave whispers out.

## Security

- The addon only reads chat events and draws coloured squares. It sends no
  addon messages and runs nothing it receives. The slang hints only match
  words from a fixed list.
- Text from other players is only ever **displayed**. Nothing in a chat
  message can make the app or the addon do anything.
- Translated replies are cleaned before they're copied: they're kept to one
  line, any leading `/` is removed (so a reply can never become a command
  like `/run`), `|` codes are removed, and they're cut at WoW's
  255-character limit.
- When Claude is used, chat text is passed as quoted data with instructions
  never to follow anything written in it.
- Chat spam can't run up your quota or bill: repeated messages are ignored
  for a minute, and the app makes at most 30 translation requests a minute.
- Dependencies are pinned in `app/requirements.txt`.

Found a security problem? Please open a private
[security advisory](../../security/advisories/new) instead of a public issue.

## Run from source

Needs Python 3.12+. In `app/`, run `start.bat` (or
`python forever_translate.py`). `demo.bat` shows sample chat without WoW.

## License

MIT. See [LICENSE](LICENSE). World of Warcraft is a trademark of Blizzard
Entertainment. This project is not affiliated with or endorsed by Blizzard.
