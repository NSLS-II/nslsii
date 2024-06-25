from ldap3 import Server, Connection, NTLM
from ldap3.core.exceptions import LDAPInvalidCredentialsResult

import json
import re
import redis
import httpx
import warnings
from datetime import datetime
from getpass import getpass
from redis_json_dict import RedisJSONDict
from typing import Dict, Any
import argparse

data_session_re = re.compile(r"^pass-(?P<proposal_number>\d+)$")

nslsii_api_client = httpx.Client(base_url="https://api.nsls2.bnl.gov")


def get_current_cycle() -> str:
    cycle_response = nslsii_api_client.get(
        f"/v1/facility/nsls2/cycles/current"
    ).raise_for_status()
    return cycle_response.json()["cycle"]


def validate_proposal(data_session_value, beamline) -> Dict[str, Any]:

    data_session_match = data_session_re.match(data_session_value)

    if data_session_match is None:
        raise ValueError(
            f"RE.md['data_session']='{data_session_value}' "
            f"is not matched by regular expression '{data_session_re.pattern}'"
        )

    try:
        current_cycle = get_current_cycle()
        proposal_number = data_session_match.group("proposal_number")
        proposal_response = nslsii_api_client.get(
            f"/v1/proposal/{proposal_number}"
        ).raise_for_status()
        proposal_data = proposal_response.json()["proposal"]
        if "error_message" in proposal_data:
            raise ValueError(
                f"while verifying data_session '{data_session_value}' "
                f"an error was returned by {proposal_response.url}: "
                f"{proposal_data}"
            )
        else:
            if current_cycle not in proposal_data["cycles"]:
                raise ValueError(
                    f"Proposal {data_session_value} is not valid in the current NSLS2 cycle ({current_cycle})."
                )
            if beamline.upper() not in proposal_data["instruments"]:
                raise ValueError(
                    f"Wrong beamline ({beamline.upper()}) for proposal {data_session_value} ({', '.join(proposal_data['instruments'])})."
                )
            # data_session is valid!

    except httpx.RequestError as rerr:
        # give the user a warning but allow the run to start
        proposal_data = {}
        warnings.warn(
            f"while verifying data_session '{data_session_value}' "
            f"the request {rerr.request.url!r} failed with "
            f"'{rerr}'"
        )

    finally:
        return proposal_data


def authenticate(username):

    auth_server = Server("dc2.bnl.gov", use_ssl=True)

    try:
        connection = Connection(
            auth_server,
            user=f"BNL\\{username}",
            password=getpass("Password : "),
            authentication=NTLM,
            auto_bind=True,
            raise_exceptions=True,
        )
        print(f"\nAuthenticated as : {connection.extend.standard.who_am_i()}")

    except LDAPInvalidCredentialsResult:
        raise RuntimeError(f"Invalid credentials for user '{username}'.") from None


def should_they_be_here(username, new_data_session, beamline):

    user_access_json = nslsii_api_client.get(f"/v1/data-session/{username}").json()

    if "nsls2" in user_access_json["facility_all_access"]:
        return True

    elif beamline.lower() in user_access_json["beamline_all_access"]:
        return True

    elif new_data_session in user_access_json["data_sessions"]:
        return True

    return False


class AuthorizationError(Exception): ...


def sync_experiment(proposal_number, beamline, verbose=False, prefix=""):

    redis_client = redis.Redis(host=f"info.{beamline.lower()}.nsls2.bnl.gov")

    md = RedisJSONDict(redis_client=redis_client, prefix=prefix)

    new_data_session = f"pass-{proposal_number}"
    username = input("Username : ")

    if (new_data_session == md.get("data_session")) and (
        username == md.get("username")
    ):

        warnings.warn(
            f"Experiment {new_data_session} was already started by the same user."
        )

    else:

        proposal_data = validate_proposal(new_data_session, beamline)
        users = proposal_data.pop("users")

        authenticate(username)

        if not should_they_be_here(username, new_data_session, beamline):
            raise AuthorizationError(
                f"User '{username}' is not allowed to take data on proposal {new_data_session}"
            )

        pi_name = ""
        for user in users:
            if user.get("is_pi"):
                pi_name = (
                    f'{user.get("first_name", "")} {user.get("last_name", "")}'.strip()
                )

        md["data_session"] = new_data_session
        md["username"] = username
        md["start_datetime"] = datetime.now().isoformat()
        md["cycle"] = get_current_cycle()
        md["proposal"] = {
            "proposal_id": proposal_data.get("proposal_id"),
            "title": proposal_data.get("title"),
            "type": proposal_data.get("type"),
            "pi_name": pi_name,
        }

        print(f"Started experiment {new_data_session}.")
        if verbose:
            print(json.dumps(proposal_data, indent=2))
            print("Users:")
            print(users)


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
        proposal_number=args.proposal, beamline=args.beamline, verbose=args.verbose
    )
