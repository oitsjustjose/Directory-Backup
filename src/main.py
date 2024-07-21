import argparse
import logging
from pathlib import Path
from datetime import datetime
from datetime import date

import os
import time
from src.watcher import Watcher
from enum import Enum


class LogLevel(Enum):
    debug = "DEBUG"
    info = "INFO"
    warning = "WARNING"
    error = "ERROR"
    critical = "CRITICAL"

    def __str__(self):
        return self.value


def __init_dirs(logs: str, dest: str):
    if not os.path.exists(dest):
        os.makedirs(dest)
    if not os.path.exists(logs):
        os.mkdir(logs)


def __get_log_version(today: date) -> int:
    existing = list(filter(lambda x: x.startswith(str(today)), os.listdir("./logs")))
    return len(existing) + 1


def main(
    source: Path,
    destination: Path,
    ignore_pattern: str,
    log_level: LogLevel,
    log_output: Path,
) -> None:
    """
    Main method for this entire program
    Arguments:
        source (pathlib.Path): The path to watch
        destination (pathlib.Path): The path to copy directory changes to
        ignore_pattern (str): A regex pattern used to ignore backing up certain directories
        log_level (LogLevel): The verbosity at which logs should be written. Defaults to ERROR from argparse
        log_output (pathlib.Path): The path to a folder where log outputs should be written
    """
    __init_dirs(log_output, destination)

    now = datetime.now()

    logger = logging.getLogger(__name__)
    logger.setLevel(str(log_level))

    filename = f"{now.date()}-{__get_log_version(now.date())}.log"
    filename = log_output.joinpath(filename).resolve().absolute()

    logging.basicConfig(filename=filename)

    logger.info(f"Watching directory {source}")
    logger.info(f"Backing up to {destination}")

    # Spin up a different thread for each subdirectory to keep up with performance
    subdirs = sorted(
        list(
            filter(
                lambda x: source.joinpath(x).resolve().is_dir(),
                os.listdir(source),
            )
        )
    )

    watchers = [
        Watcher(
            logger,
            source.joinpath(subdir).resolve().absolute(),
            destination.joinpath(subdir).resolve().absolute(),
            ignore_pattern,
        )
        for subdir in subdirs
    ]

    [x.start() for x in watchers]
    
    while True:
        try:
            time.sleep(0.01)
        except KeyboardInterrupt:
            print("Quitting...")
            [x.stop() for x in watchers]
            break
        
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
    parser.add_argument(
        "-i",
        "--ignore-pattern",
        help="A regex string used to match against any paths that should be ignored.",
        default="",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        help="Changes logging level to show all debug messages.",
        default=LogLevel.error,
        type=LogLevel,
        choices=list(LogLevel),
    )
    parser.add_argument(
        "-o",
        "--log-output",
        help=f"Sets the location of the log output (defaults to {Path('./logs').resolve().absolute()}).",
        default=Path("./logs").resolve().absolute(),
    )

    try:
        args = parser.parse_args()
    except Exception as e:
        print("Failed to start application:")
        print(e)

    source = Path(args.source)
    destination = Path(args.destination)
    log_output = Path(args.log_output)

    if not source.is_dir():
        print(
            f"Argument source resolves to {source.resolve().absolute()}, which is not a directory."
        )
    elif destination.exists() and not destination.is_dir():
        print(
            f"Argument destination resolves to {destination.resolve().absolute()}, which is not a directory."
        )
    elif log_output.exists() and not log_output.is_dir():
        print(
            f"Argument log_output resolves to {log_output.resolve().absolute()}, which is not a directory."
        )
    else:
        main(source, destination, args.ignore_pattern, args.log_level, log_output)
