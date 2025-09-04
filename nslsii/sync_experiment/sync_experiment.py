from __future__ import annotations

import argparse
import json
import re
import warnings
from datetime import datetime
from getpass import getpass
from pathlib import Path
from typing import Any

import httpx
import redis
import yaml
from ldap3 import NTLM, Connection, Server
from ldap3.core.exceptions import LDAPInvalidCredentialsResult, LDAPSocketOpenError
from redis_json_dict import RedisJSONDict

data_session_re = re.compile(r"^pass-(?P<proposal_number>\d+)$")

nslsii_api_client = httpx.Client(base_url="https://api.nsls2.bnl.gov")


def get_current_cycle() -> str:
    cycle_response = nslsii_api_client.get(
        "/v1/facility/nsls2/cycles/current"
    ).raise_for_status()
    return cycle_response.json()["cycle"]


def is_commissioning_proposal(proposal_number, beamline) -> bool:
    """True if proposal_number is registered as a commissioning proposal; else False."""
    commissioning_proposals_response = nslsii_api_client.get(
        f"/v1/proposals/commissioning?beamline={beamline}"
    ).raise_for_status()
    commissioning_proposals = commissioning_proposals_response.json()[
        "commissioning_proposals"
    ]
    return proposal_number in commissioning_proposals


def validate_proposal(data_session_value, beamline) -> dict[str, Any]:
    proposal_data = {}
    data_session_match = data_session_re.match(data_session_value)

    if data_session_match is None:
        msg = f"RE.md['data_session']='{data_session_value}' "
        msg += f"is not matched by regular expression '{data_session_re.pattern}'"
        raise ValueError(msg)

    try:
        current_cycle = get_current_cycle()
        proposal_number = data_session_match.group("proposal_number")
        proposal_commissioning = is_commissioning_proposal(proposal_number, beamline)
        proposal_response = nslsii_api_client.get(
            f"/v1/proposal/{proposal_number}"
        ).raise_for_status()
        proposal_data = proposal_response.json()["proposal"]
        if "error_message" in proposal_data:
            msg = f"while verifying data_session '{data_session_value}' "
            msg += f"an error was returned by {proposal_response.url}: "
            msg += f"{proposal_data}"
            raise ValueError(msg)
        if not proposal_commissioning and current_cycle not in proposal_data["cycles"]:
            msg = f"Proposal {data_session_value} is not valid in the current NSLS2 cycle ({current_cycle})."
            raise ValueError(msg)
        if beamline.upper() not in proposal_data["instruments"]:
            msg = f"Wrong beamline ({beamline.upper()}) for proposal {data_session_value} ({', '.join(proposal_data['instruments'])})."
            raise ValueError(msg)
            # data_session is valid!

    except httpx.RequestError as rerr:
        # give the user a warning but allow the run to start
        warnings.warn(
            f"while verifying data_session '{data_session_value}' "
            f"the request {rerr.request.url!r} failed with "
            f"'{rerr}'",
            stacklevel=2,
        )

    return proposal_data


config_files = [
    Path.expanduser("~/.config/n2sn_tools.yml"),
    "/etc/n2sn_tools.yml",
]


def authenticate(
    username,
):
    config = None
    for fn in config_files:
        try:
            with Path.open(fn) as f:
                config = yaml.safe_load(f)
        except OSError:
            pass
        else:
            break

    if config is None:
        msg = "Unable to open a config file"
        raise RuntimeError(msg)

    server = config.get("common", {}).get("server")

    if server is None:
        msg = "Server name not found!"
        raise RuntimeError(msg)

    auth_server = Server(server, use_ssl=True)

    try:
        connection = Connection(
            auth_server,
            user=f"BNL\\{username}",
            password=getpass("Password : "),
            authentication=NTLM,
            auto_bind=True,
            raise_exceptions=True,
        )
        print(f"\nAuthenticated as : {connection.extend.standard.who_am_i()}")  # noqa : T201

    except LDAPInvalidCredentialsResult:
        msg = f"Invalid credentials for user '{username}'."
        raise RuntimeError(msg) from None
    except LDAPSocketOpenError:
        print(f"{server} server connection failed...")  # noqa : T201


def should_they_be_here(username, new_data_session, beamline):
    user_access_json = nslsii_api_client.get(f"/v1/data-session/{username}").json()

    return (
        "nsls2" in user_access_json["facility_all_access"]
        or beamline.lower() in user_access_json["beamline_all_access"]
        or new_data_session in user_access_json["data_sessions"]
    )


class AuthorizationError(Exception): ...


def switch_redis_proposal(
    proposal_number: int | str,
    beamline: str,
    username: str | None = None,
    prefix: str = "",
) -> RedisJSONDict:
    """Update information in RedisJSONDict for a specific beamline

    Parameters
    ----------
    proposal_number : int or str
        number of the desired proposal, e.g. `123456`
    beamline : str
        normalized beamline acronym, case-insensitive, e.g. `SMI` or `sst`
    username : str or None
        login name of the user assigned to the proposal; if None, current user will be kept
    prefix : str
        optional prefix to identify a specific endstation, e.g. `opls`

    Returns
    -------
    md : RedisJSONDict
        The updated redis dictionary.
    """

    redis_client = redis.Redis(host=f"info.{beamline.lower()}.nsls2.bnl.gov")
    redis_prefix = f"{prefix}-" if prefix else ""
    md = RedisJSONDict(redis_client=redis_client, prefix=redis_prefix)
    username = username or md.get("username")

    new_data_session = f"pass-{proposal_number}"
    if (new_data_session == md.get("data_session")) and (
        username == md.get("username")
    ):
        # The cycle needs to get updated regardless of experiment status
        md["cycle"] = (
            "commissioning"
            if is_commissioning_proposal(str(proposal_number), beamline)
            else get_current_cycle()
        )
        warnings.warn(
            f"Experiment {new_data_session} was already started by the same user.",
            stacklevel=2,
        )

    else:
        if not should_they_be_here(username, new_data_session, beamline):
            msg = f"User '{username}' is not allowed to take data on proposal {new_data_session}"
            raise AuthorizationError(msg)

        proposal_data = validate_proposal(new_data_session, beamline)
        users = proposal_data.pop("users")
        pi_name = ""
        for user in users:
            if user.get("is_pi"):
                pi_name = (
                    f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                )
        md["data_session"] = new_data_session  # e.g. "pass-123456"
        md["username"] = username
        md["start_datetime"] = datetime.now().isoformat()
        md["tiled_access_tags"] = (
            new_data_session  # Used by bluesky-tiled-writer, not metadata
        )
        md["cycle"] = (
            "commissioning"
            if is_commissioning_proposal(str(proposal_number), beamline)
            else get_current_cycle()
        )
        md["proposal"] = {
            "proposal_id": proposal_data.get("proposal_id"),
            "title": proposal_data.get("title"),
            "type": proposal_data.get("type"),
            "pi_name": pi_name,
        }

        print(f"Started experiment {md['data_session']} by {md['username']}.")  # noqa : T201

    return md


def sync_experiment(proposal_number, beamline, verbose=False, prefix=""):
    # Authenticate the user
    username = input("Username : ")
    authenticate(username)

    normalized_beamlines = {
        "sst1": "sst",
        "sst2": "sst",
    }
    redis_beamline = normalized_beamlines.get(beamline.lower(), beamline)

    md = switch_redis_proposal(
        proposal_number, beamline=redis_beamline, username=username, prefix=prefix
    )

    if verbose:
        print(json.dumps(md, indent=2))  # noqa : T201

    return md


def main():
    # Used by the `sync-experiment` command

    parser = argparse.ArgumentParser(
        description="Start or switch beamline experiment and record it in Redis"
    )
    parser.add_argument(
        "-b",
        "--beamline",
        dest="beamline",
        type=str,
        help="Which beamline (e.g. CHX)",
        required=True,
    )
    parser.add_argument(
        "-e",
        "--endstation",
        dest="prefix",
        type=str,
        help="Prefix for redis keys (e.g. by endstation)",
        required=False,
    )
    parser.add_argument(
        "-p",
        "--proposal",
        dest="proposal",
        type=int,
        help="Which proposal (e.g. 123456)",
        required=True,
    )
    parser.add_argument("-v", "--verbose", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    sync_experiment(
        proposal_number=args.proposal,
        beamline=args.beamline,
        verbose=args.verbose,
        prefix=args.prefix,
    )
