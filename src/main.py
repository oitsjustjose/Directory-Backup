import argparse
import logging
import sys
from datetime import datetime

import os
from .watcher import Watcher


def __init_dirs(dest: str):
    if not os.path.exists(dest):
        os.makedirs(dest)
    if not os.path.exists("./logs"):
        os.mkdir("./logs")


def main(source: str, destination: str) -> None:
    """"""
    __init_dirs(destination)

    logger = logging.getLogger(__name__)
    logger.setLevel("DEBUG")
    logging.basicConfig(filename=f"./logs/{datetime.now()}.log")

    logger.info(f"Watching directory {source}")
    logger.info(f"Backing up to {destination}")

    try:
        watcher = Watcher(logger, source, destination)
        logger.info("Watcher started")
        watcher.start()
    except KeyboardInterrupt:
        logger.info("Stopping watcher")
        watcher.stop()
        logger.info("Watcher stopped -- quitting!")


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
