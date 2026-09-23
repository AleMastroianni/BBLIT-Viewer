"""The proof that no wall was lost when the flag Invisible walls went:
two dumps of `tools/wall_runs_dump.py`, one from the
code before the change and one from the code after, compared level by
level as SETS of runs. Hard walls "only the invisible ones" plus Steps must
draw exactly the runs the old flag drew.

    .venv/Scripts/python tools/wall_flag_proof.py OLD.json NEW.json

Sets, not lists: a run on the edge two stacked blocks share is now one
piece per block, floor to ceiling (the pieces pile up with their true
limits), where the old code drew one panel from the ground.

Result: old code at 02a4307, new code with the walls on the game's faces,
79 levels, 0 with a difference; 29 365 invisible
hard-wall runs and 70 240 step runs on both sides.
"""
import json
import sys


def main():
    old = json.load(open(sys.argv[1]))
    new = json.load(open(sys.argv[2]))
    differences = 0
    invisible_old = invisible_new = steps = reclassified = 0
    for name in sorted(set(old) | set(new)):
        o, n = old.get(name), new.get(name)
        if o is None or n is None:
            print("MISSING", name)
            differences += 1
            continue
        hard_o = {tuple(map(str, r)) for r in o["hard"]}
        hard_n = {tuple(map(str, r)) for r in n["hard"]}
        unseen_o = {k for k in hard_o if k[5] == "False"}
        unseen_n = {k for k in hard_n if k[5] == "False"}
        # the steps without their last field, the hole flag: a hole step over
        # a block with ground under it became a plain step
        # (collision.grounded), the same run under the Steps flag
        # (the edge, its visibility, its low side): the grounds of a run are
        # the run's extremes, and the pieces of a split run have their own
        steps_o = {tuple(map(str, r[:4] + r[6:8])) for r in o["steps"]}
        steps_n = {tuple(map(str, r[:4] + r[6:8])) for r in n["steps"]}
        holes_o = {tuple(map(str, r[:4] + r[6:8])) for r in o["steps"] if r[8]}
        holes_n = {tuple(map(str, r[:4] + r[6:8])) for r in n["steps"] if r[8]}
        invisible_old += len(unseen_o)
        invisible_new += len(unseen_n)
        steps += len(steps_n)
        reclassified += len(holes_o - holes_n)
        if hard_o != hard_n or unseen_o != unseen_n or steps_o != steps_n:
            print(f"DIFF {name}: hard runs {len(hard_o ^ hard_n)}, invisible {len(unseen_o ^ unseen_n)}, "
                  f"steps {len(steps_o ^ steps_n)}")
            differences += 1
    print(f"levels {len(old)}, levels with a difference {differences}, "
          f"invisible walls old {invisible_old} new {invisible_new}, steps {steps}, "
          f"hole steps that became steps {reclassified}")
    sys.exit(1 if differences else 0)


if __name__ == "__main__":
    main()
