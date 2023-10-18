import json
import os
import re
import sys
import time


TRANSFER_LABEL = f"DME Transfer submitted on \
{time.strftime('%Y-%m-%d', time.localtime(time.time()))}"

get_input = getattr(__builtins__, "raw_input", input)


def load_data_from_file(filepath):
    # Load a set of saved tokens
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        data = json.load(f)

    return data


def save_data_to_file(filepath, key, data):
    # Save data to a file
    try:
        store = load_data_from_file(filepath)
    except:
        store = {}

    if len(store) > 0:
        store[key] = data
    with open(filepath, "w") as f:
        json.dump(store, f)


def validate_endpoint_id(id=None):
    uuid_regex = (
        "^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$"
    )
    uuid_pattern = re.compile(uuid_regex)

    if bool(uuid_pattern.match(id)):
        return True
    else:
        print("Source endpoint ID is not a valid UUID - aborting.")
        sys.exit(1)
