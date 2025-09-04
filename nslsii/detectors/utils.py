from __future__ import annotations

from pathlib import Path


def makedirs(path: Path, mode: int = 0o777) -> list[str]:
    """Recursively make directories and set permissions"""
    # Permissions not working with os.makedirs -
    # See: http://stackoverflow.com/questions/5231901
    if path is None or str(path) == "" or path.exists():
        return []

    head, _ = Path.split(path)
    ret = makedirs(head, mode)
    try:
        Path.mkdir(path)
    except OSError as ex:
        if "File exists" not in str(ex):
            raise

    Path.chmod(path, mode)
    ret.append(path)
    return ret


def ordered_dict_move_to_beginning(od, key):
    if key not in od:
        return

    value = od[key]
    items = [(k, v) for k, v in od.items() if k != key]
    od.clear()
    od[key] = value
    od.update(items)


def make_filename_add_subdirectory(
    fn, read_path, write_path, *, make_directories=True, hash_characters=5
):
    """
    tag on a portion of the hash to reduce the number of files in one
    directory

    Parameters
    ----------
    fn : str
        Filename
    read_path : str
        Read path
    write_path : str
        Write path
    make_directories : bool, optional
        Make directories and set permissions (on the read_path)
    hash_characters : int, optional
        Number of characters to use from the hash
    """
    hash_portion = fn[:hash_characters]
    read_path = Path(read_path) / hash_portion
    write_path = Path(write_path) / hash_portion

    if make_directories:
        makedirs(read_path)
    return fn, read_path, write_path
