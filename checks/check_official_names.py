"""The level names in the menu (tools/levels.py) against the game's own texts.

    .venv/Scripts/python checks/check_official_names.py

Read again from the disc with game_texts.py (finding 291), in English and in
Italian:
1. every game title must be the LS01 text it names (`ls01`, plus the `_8`
   suffix for a variant);
2. every game note must be the cards it names ("cards"), joined by " + ",
   and each of them a 120-tick card that the level's own rules show;
3. the null: the same titles compared with the text one index further on
   must all fail, or the comparison proves nothing.
Then it lists the candidate cards not used: a card can be a sign or a
hint as well as the name of a sub-level (finding 291), so the choice is
made by whoever reads them in the game.
Exits with 1 if anything differs.
"""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from game import game_texts as gt  # noqa: E402
from game import levels  # noqa: E402
from game import loadscript  # noqa: E402
from support import paths  # noqa: E402
from viewer import sections  # noqa: E402


def load(name):
    files = [f for f in os.listdir(paths.DATA_BZE) if f.upper() == name.upper() + ".BZE"]
    if not files:
        return None
    return sections(os.path.join(paths.DATA_BZE, files[0]), os.path.join(paths.PROJECT_DIR, "extracted"))


def main():
    errors = 0
    selector = load("LS01")
    ls01 = gt.language_blocks(selector[3])
    titles, notes, missed, null_hits, n_titles, user_notes = 0, 0, [], 0, 0, 0
    checked_files = set()
    for levid, file, _era, title, _part, note, _extra in levels.all_entries():
        if isinstance(title, dict) and "ls01" in title:
            n_titles += 1
            i, suffix = title["ls01"], title.get("suffix", "")
            for lang in ("en", "it"):
                if title[lang] != gt.clean(ls01[lang][i]) + suffix:
                    print(f"{file}: title {title[lang]!r} is not LS01 text {i} {gt.clean(ls01[lang][i])!r}")
                    errors += 1
                null_hits += title[lang] == gt.clean(ls01[lang][i + 1]) + suffix
            titles += 1
        if file in checked_files or file.upper().startswith(("CC", "TITLE", "CREDITS", "LS01")):
            continue
        checked_files.add(file)
        sec = load(file)
        if sec is None or 3 not in sec:
            continue
        texts = gt.language_blocks(sec[3])
        if not texts:
            continue
        shown = gt.candidates(loadscript.parse(sec[1])[0], texts)
        used = note.get("cards", []) if isinstance(note, dict) else []
        if isinstance(note, dict) and "cards" not in note:
            # the user's own note, translated: both languages, no game text to match
            user_notes += 1
            if not (note.get("en") and note.get("it")):
                print(f"{file}: user note {note} lacks a language")
                errors += 1
        elif isinstance(note, dict):
            notes += 1
            expected = gt.names_of(texts, used)
            if (not used or any(i not in shown for i in used)
                    or any(note[lang] != expected[lang] for lang in ("en", "it"))):
                print(f"{file}: note {note} is not the game's cards {expected}")
                errors += 1
        unused = [i for i in shown if i not in used]
        if unused:
            missed.append(f"{file}: " + " | ".join(f"{gt.clean(texts['en'][i])} / {gt.clean(texts['it'][i])}"
                                                   for i in unused))
    print(f"1. {titles} game titles (in {n_titles} entries) equal to their LS01 text, "
          f"null (next text): {null_hits} matches")
    print(f"2. {notes} files with game area names equal to their cards; {user_notes} user notes in both languages")
    print("candidate cards not used (to be judged in the game):")
    for line in missed:
        print("   " + line)
    errors += null_hits > 0
    print("all consistent" if not errors else f"{errors} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
