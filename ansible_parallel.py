import os
import asyncio
from typing import Tuple
from time import perf_counter
from shutil import get_terminal_size
import subprocess


import argparse


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("playbook", nargs="+")
    return parser.parse_known_args()


def prepare_chunk(playbook, chunk: str) -> Tuple[str, str, str]:
    """Parse a chunk of ansible-playbook output.

    Given an ansible-playbook output chunk, like:

    TASK [staging : Install sudo] ********************************************
    ok: [staging1.eeple.net]

    return a tree-tuple:
    - Chunk type:
       - "OK", "CHANGED", "FAILED", "UNREACHABLE": Ansible task status.
       - "TASK": Unknown task type, yet probably a task.
       - "RECAP": The big "PLAY RECAP" section at the end of a run.
    - playbook name
    - the actual chunk.

    """
    lines = chunk.split("\n")
    if len(lines) >= 2:
        if "PLAY RECAP" in chunk:
            return ("RECAP", playbook, chunk)
        if "ok:" in lines[1]:
            return ("OK", playbook, chunk)
        if "changed:" in lines[1]:
            return ("CHANGED", playbook, chunk)
        if "failed:" in lines[1] or "fatal:" in lines[1]:
            return ("FAILED", playbook, chunk)
        if "unreachable:" in lines[1]:
            return ("UNREACHABLE", playbook, chunk)
    return ("TASK", playbook, chunk)


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
    while True:
        line = (await process.stdout.readline()).decode()
        if not line:
            break
        if line == "\n":
            chunk = "".join(task) + line
            await results.put(prepare_chunk(playbook, chunk))
            task = []
        else:
            task.append(line)
    if task:
        chunk = "".join(task)
        await results.put(prepare_chunk(playbook, chunk))

    await process.wait()
    await results.put(("DONE", playbook, ""))


FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

DISABLE_CURSOR = "\033[?25l"
ENABLE_CURSOR = "\033[?25h"


def truncate(string, max_width):
    if len(string) <= max_width:
        return string
    return string[: max_width - 1] + "…"


async def show_progression(results):
    recaps = {}
    starts = {}
    ends = {}
    currently_running = []
    frameno = 0
    print(DISABLE_CURSOR, end="")
    columns, _ = get_terminal_size()
    try:
        while True:
            result = await results.get()
            if not result:
                break
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
            if msgtype in ("CHANGED", "FAILED", "UNREACHABLE"):
                print(msg)
            status_line = (
                FRAMES[frameno % len(FRAMES)] + " "
                f"{len(currently_running)} playbook{'s' if len(currently_running) > 1 else ''} running: "
                f"{', '.join(currently_running)}"
            )
            print(
                "\033[0J",  # ED (Erase In Display) with parameter 0:
                # Erase from the active position to the end of the screen.
                truncate(status_line, max_width=columns),
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
