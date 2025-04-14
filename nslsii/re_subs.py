from io import TextIOWrapper
import json
import os
from pathlib import Path

class BlueskyDocJSONWriter:

    def __init__(self, write_directory: Path):
        if not os.path.exists(write_directory):
            raise FileNotFoundError(
                f"Directory does not exist: {write_directory}"
            )
        elif not os.access(write_directory, os.W_OK):
            raise PermissionError(
                f"Cannot write to directory: {write_directory}"
            )
        self.write_json_file: bool = False
        self.write_directory = write_directory
        self.output_file: TextIOWrapper | None  = None
        self.document_cache = []

    def __call__(self, name: str, doc: dict):
        if self.write_json_file:
            if name == "start":
                self.output_file = open(
                    os.path.join(self.write_directory, f"{doc['uid']}.json"), "w"
                )

            if self.output_file is None:
                # If we don't have an open file, just drop the docs on the floor.
                pass
            else:
                self.document_cache.append({name: doc})

                if name == "stop":
                    json.dump(
                        self.document_cache,
                        self.output_file,
                        indent=4,
                        sort_keys=True,
                    )
                    self.document_cache = []
                    self.output_file.close()
                    self.output_file = None
        elif self.output_file is not None:
            # If we toggled off writing, close any open file.
            self.document_cache = []
            self.output_file.close()
            self.output_file = None


class BlueskyDocStreamPrinter:
    """
    Print documents to stdout.
    """

    def __init__(self):
        self.print_docs_to_stdout = False

    def __call__(self, name: str, doc: dict):
        if self.print_docs_to_stdout:
            print("========= Emitting Doc =============")
            print(f"{name = }")
            print(f"{json.dumps(doc, indent=4)}")
            print("============ Done ==================")
