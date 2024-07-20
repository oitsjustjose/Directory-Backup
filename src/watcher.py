import os
import shutil
from logging import Logger
from pathlib import Path
from time import sleep

from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileSystemEventHandler,
    FileSystemMovedEvent,
)
from watchdog.observers import Observer


class Watcher:
    def __init__(self, logger: Logger, source: str, destination: str):
        self.logger = logger
        self.source = Path(source).absolute()
        self.dest = Path(destination).absolute()
        self.observer = Observer()
        self.handler = Handler(self.logger, self.source, self.dest)
        self.running = False

    def start(self):

        self.observer.schedule(self.handler, self.source, recursive=True)
        self.logger.info("Custom handler has been scheduled with the Observer")

        self.observer.start()
        self.logger.info("The Observer has been started!")

        self.logger.info("Starting main loop @ 1s polling rate")
        self.running = True
        while self.running:
            sleep(1)

    def stop(self):
        self.running = False
        self.observer.stop()
        self.observer.join()


class Handler(FileSystemEventHandler):
    def __init__(self, logger: Logger, source: Path, destination: Path):
        self.logger = logger
        self.source = source
        self.dest = destination

    def __in_destination(self, path: Path) -> Path:
        """
        Given a path in the watch directory, converts it to the destination's path instead
        Arguments:
            path (pathlib.Path): The path in the original directory
        Returns:
            (pathlib.Path): The path, but in the destination directory, as absolute
        """
        # Kind of nasty, but convert to string, find & replace source with destination
        as_str = str(path).replace(str(self.source), str(self.dest))
        return Path(as_str).absolute()

    def __recursively_clean_dirs_upwards(self, path: Path) -> None:
        """
        Removes empty directories at and above the current one. Stops when it reaches a
            non-empty directory or recursive path reaches the topmost-path in the destination
        Arguments:
            path (pathlib.Path): The path (a directory) at which to start the recursive cleanup
        """
        # Base case: we've gone all the way back up to the root, and we'll never delete that..
        if path == self.dest:
            return
        # Ok, the path we're at has items -- no need to keep going up
        if [x for x in path.iterdir()]:
            return
        # Otherwise, we have an empty directory that we should delete
        shutil.rmtree(path.absolute())
        # Go up a directory and repeat!
        up = path.joinpath("..").resolve().absolute()
        self.__recursively_clean_dirs_upwards(up)

    def on_created(self, event: FileCreatedEvent) -> None:
        """
        Called upon creation of a new file. Upon creation, will find the same subdirectory
            in the destination directory, making any non-existing subdirectories recursively,
            then finally copying the file
        Arguments:
            event (watchdog.events.FileCreatedEvent): the event fired
        """
        if event.is_directory:
            return
        src = Path(event.src_path).absolute()
        in_dest = self.__in_destination(src)
        os.makedirs(in_dest.parent.absolute(), exist_ok=True)
        shutil.copy2(src, self.__in_destination(src))

    def on_modified(self, event: FileModifiedEvent) -> None:
        """
        Called upon modification of a file, at which point the backed up file is
            deleted and then re-copied from the source.
        Arguments:
            event (watchdog.events.FileModifiedEvent): the event fired
        """
        if event.is_directory:
            return

        src = Path(event.src_path).absolute()
        in_dest = self.__in_destination(src)

        if in_dest.exists():
            in_dest.unlink()

        # Copy over the new file, making required subdirectories
        os.makedirs(in_dest.parent.absolute(), exist_ok=True)
        shutil.copy2(src, in_dest)

    def on_moved(self, event: FileSystemMovedEvent):
        """
        Called upon renaming / relocation of a file. Upon movement, it entirely deletes the
            prior location as mapped in the destination directory, then essentially does the same
            thing as `on_created` for a new directory. Cleans up parent directories from the old
            mapping to ensure no empty folders are just left behind
        Arguments:
            event (watchdog.events.FileSystemMovedEvent): the event fired
        """
        if event.is_directory:
            return

        src = Path(event.src_path).absolute()
        dest = Path(event.dest_path).absolute()

        in_dest_before = self.__in_destination(src)
        in_dest = self.__in_destination(dest)

        # Copy over the new file, making required subdirectories
        os.makedirs(in_dest.parent.absolute(), exist_ok=True)
        shutil.copy2(dest, in_dest)

        # Delete the old file, try to delete parent folder if it's empty
        if in_dest_before.exists():
            in_dest_before.unlink()

        self.__recursively_clean_dirs_upwards(in_dest_before.parent.absolute())

    def on_deleted(self, event: FileDeletedEvent) -> None:
        """
        Called upon deletion of a file, at which point the backed up file is deleted
        Arguments:
            event (watchdog.events.FileDeletedEvent): the event fired
        """
        if event.is_directory:
            return

        in_dest = self.__in_destination(event.src_path)

        if in_dest.exists():
            in_dest.unlink()

        self.__recursively_clean_dirs_upwards(in_dest.parent.absolute())
