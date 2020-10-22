import os
import asyncio
from time import perf_counter
import subprocess


import argparse


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("playbook", nargs="+")
    return parser.parse_known_args()


async def run_playbook(playbook, args, results):
    await results.put(("START", playbook, ""))
    process = await asyncio.create_subprocess_exec(
        "ansible-playbook",
        playbook,
        *args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, "ANSIBLE_FORCE_COLOR": "1"},
    )
    task = []
    while line := (await process.stdout.readline()).decode():
        if line == "\n":
            chunk = "".join(task) + line
            await results.put(
                ("RECAP" if "PLAY RECAP" in chunk else "TASK", playbook, chunk)
            )
            task = []
        else:
            task.append(line)
    if task:
        chunk = "".join(task)
        await results.put(
            ("RECAP" if "PLAY RECAP" in chunk else "TASK", playbook, chunk)
        )

    await process.wait()
    await results.put(("DONE", playbook, ""))


FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

DISABLE_CURSOR = "\033[?25l"
ENABLE_CURSOR = "\033[?25h"


def truncate(string, max_width=120):
    if len(string) < max_width:
        return string
    return string[:max_width] + "…"


async def show_progression(results):
    recaps = {}
    starts = {}
    ends = {}
    currently_running = []
    frameno = 0
    print(DISABLE_CURSOR, end="")
    try:
        while result := await results.get():
            frameno += 1
            msgtype, playbook, msg = result
            if msgtype == "START":
                starts[playbook] = perf_counter()
                currently_running.append(playbook)
            if msgtype == "DONE":
                currently_running.remove(playbook)
                ends[playbook] = perf_counter()
            if msgtype == "RECAP":
                recaps[playbook] = msg
            print(
                FRAMES[frameno % len(FRAMES)],
                f"{len(currently_running)} playbook{'s' if len(currently_running) > 1 else ''} running:",
                f"{truncate(', '.join(currently_running))}",
                end="\r",
            )
    finally:
        print(ENABLE_CURSOR, end="")
    for playbook, recap in recaps.items():
        print(
            f"# Playbook {playbook}, ran in {ends[playbook] - starts[playbook]:.0f}s",
            end="\n\n",
        )
        for line in recap.split("\n"):
            if "PLAY RECAP" not in line:
                print(line)


async def amain():
    args, remaining_args = parse_args()
    results = asyncio.Queue()
    asyncio.create_task(show_progression(results))
    await asyncio.gather(
        *[run_playbook(playbook, remaining_args, results) for playbook in args.playbook]
    )
    await results.put(None)


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
