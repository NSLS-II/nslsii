import json
import os
from pathlib import Path

class JSONBlueskyDocWriter:

    def __init__(self, write_directory: Path):
        if not os.path.exists(write_directory):
            raise FileNotFoundError(
                f"Directory does not exist: {write_directory}"
            )
        elif not os.access(write_directory, os.W_OK):
            raise PermissionError(
                f"Cannot write to directory: {write_directory}"
            )
        self.write_directory = write_directory
        self.output_file = None
        self.docs_cache = {}

    def __call__(self, name: str, doc: dict):
        if name == "start":
            self.output_file = open(
                os.path.join(self.write_directory, f"{doc['uid']}.json"), "w"
            )
            self.output_file.write("[\n")
        elif self.output_file is None:
            raise RuntimeError(
                "Dump file is not open. Callback must recieve a start document first!"
            )

        self.output_file.write(json.dumps({"name": name, "doc": doc}, indent=4) + ",\n")

        if name == "stop":
            self.output_file.write("\n]\n")
            self.output_file.close()
            self.output_file = None


def dump_doc_to_stdout(name: str, doc: dict):
    print("========= Emitting Doc =============")
    print(f"{name = }")
    print(f"{json.dumps(doc, indent=4)}")
    print("============ Done ==================")


