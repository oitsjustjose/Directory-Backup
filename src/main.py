import argparse
import logging
from pathlib import Path
import sys
from datetime import datetime
from datetime import date
from threading import Thread

import os
from .watcher import Watcher


def __init_dirs(dest: str):
    if not os.path.exists(dest):
        os.makedirs(dest)
    if not os.path.exists("./logs"):
        os.mkdir("./logs")

def __get_log_version(today: date) -> int:
    existing = list(filter(lambda x: x.startswith(str(today)), os.listdir("./logs")))
    return len(existing)+1


def main(source: str, destination: str) -> None:
    """"""
    __init_dirs(destination)

    now = datetime.now()

    logger = logging.getLogger(__name__)
    logger.setLevel("DEBUG")
    logging.basicConfig(filename=f"./logs/{now.date()}-{__get_log_version(now.date())}.log")

    logger.info(f"Watching directory {source}")
    logger.info(f"Backing up to {destination}")

    threads = [
        Thread(
            target=worker,
            args=(
                logger,
                Path(source).absolute().joinpath(dir),
                Path(destination).absolute().joinpath(dir),
            ),
            daemon=True,
        )
        for dir in filter(
            lambda x: os.path.isdir(Path(source).absolute().joinpath(x)),
            os.listdir(source),
        )
    ]

    try:
        [x.start() for x in threads]
        [x.join() for x in threads]
    except KeyboardInterrupt:
        print("Waiting for threads to die...")
        pass  # keyboard interrupt should be caught by each thread


def worker(logger, source: str, destination: str) -> None:
    try:
        watcher = Watcher(logger, source, destination)
        watcher.start()
    except KeyboardInterrupt:
        watcher.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--source",
        help="The directory to watch for changes. Changes will be watched in all subdirectories.",
        required=True,
    )
    parser.add_argument(
        "-d",
        "--destination",
        help="The directory to which changed files are mirrored to.",
        required=True,
    )

    try:
        args = parser.parse_args()
    except Exception as e:
        print("Failed to start application:")
        print(e)

    main(args.source, args.destination)
