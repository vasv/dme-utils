import os
import six
import sys
import uuid

from globus_sdk import (
    AuthAPIError,
    GlobusAPIError,
    GroupsClient,
    NativeAppAuthClient,
    RefreshTokenAuthorizer,
    TransferClient,
    TransferData,
)

from globus_sdk.tokenstorage import SimpleJSONFileAdapter

from helpers import (
    load_data_from_file,
    save_data_to_file,
    TRANSFER_LABEL,
    validate_endpoint_id,
)

from globus_sdk.scopes import (
    AuthScopes,
    GCSCollectionScopeBuilder,
    GroupsScopes,
    TransferScopes,
)

APP_NAME = "DME Transfer Script"
CLIENT_ID = "27637bc2-defa-41df-b16b-561543dc1e7e"
AUTH_CLIENT = NativeAppAuthClient(client_id=CLIENT_ID, app_name=APP_NAME)
SCOPES = [
    AuthScopes.openid,
    AuthScopes.email,
    AuthScopes.profile,
    GroupsScopes.all,
]
DME_GROUP_ID = "3ca64c67-9daf-11e9-855f-0e45b29ab6fa"


"""Only members of the DME Endpoint Access group can access DME endpoints

Check/confirm group membership before proceeding.

"""


def validate_group_membership(groups_client=None):
    # DME Endpoint Access Globus group
    # User must be a member of this group to access the DME endpoints

    memberships = groups_client.get_my_groups()
    try:
        dme_membership = next(m for m in memberships if m["id"] == DME_GROUP_ID)
        try:
            status = next(
                s for s in dme_membership["my_memberships"] if s["status"] == "active"
            )
        except StopIteration as error:
            print(
                f"You must be an active member of the DME Endpoint Access group to access DME endpoints"
            )
            sys.exit(1)
    except StopIteration as error:
        print(
            f"You must be a member of the DME Endpoint Access group to access DME endpoints"
        )
        print(
            f"Request membership at: https://app.globus.org/groups/3ca64c67-9daf-11e9-855f-0e45b29ab6fa/join"
        )
        sys.exit(1)


def validate_endpoint_path(
    transfer_client=None, endpoint=None, path=None, create_dest=False
):
    # Check the endpoint path exists
    try:
        transfer_client.operation_ls(endpoint, path=path)
    except GlobusAPIError as error:
        if create_dest:
            try:
                transfer_client.operation_mkdir(endpoint, path)
                print(f"Created directory: {path}")
            except GlobusAPIError as error:
                print(f"Failed to create destination path: {error.message}")
                sys.exit(1)
        else:
            print(f"Failed to get path on {endpoint}: {error.message}")
            sys.exit(1)


def get_globus_service_clients(args=None):
    # Set up Transfer and Groups service clients
    if "nondmesource" in args:
        transfer_client, groups_client = get_api_clients(
            mapped_collection=args.nondmesource
        )
    elif "nondmedest" in args:
        transfer_client, groups_client = get_api_clients(
            mapped_collection=args.nondmedest
        )
    else:
        transfer_client, groups_client = get_api_clients()

    return transfer_client, groups_client


def get_api_clients(mapped_collection=None):
    token_file_adapter = SimpleJSONFileAdapter(os.path.expanduser(".dme_tokens.json"))

    if mapped_collection:
        # Create data access scope
        transfer_scope = TransferScopes.make_mutable("all")
        data_access_scope = GCSCollectionScopeBuilder(mapped_collection).make_mutable(
            "data_access", optional=True
        )

        # Add data_access as a dependency
        transfer_scope.add_dependency(data_access_scope)

        # data_access_scope = f"https://auth.globus.org/scopes/{mapped_collection}/data_access"
        requested_scopes = SCOPES.append(transfer_scope)

    else:
        requested_scopes = SCOPES.append(TransferScopes.all)

    # Do Globus Auth login flow to get tokens
    if not token_file_adapter.file_exists():
        # Do a login flow, getting back initial tokens
        AUTH_CLIENT.oauth2_start_flow(requested_scopes=SCOPES, refresh_tokens=True)
        authorize_url = AUTH_CLIENT.oauth2_get_authorize_url()
        print(f"Log into Globus at this URL: {authorize_url}")
        auth_code = input("Enter the code you get after login here: ").strip()
        token_response = AUTH_CLIENT.oauth2_exchange_code_for_tokens(auth_code)

        # Store tokens, and extract tokens for the resource server(s) we want
        token_file_adapter.store(token_response)

    # Instantiate Transfer client
    try:
        transfer_tokens = token_file_adapter.get_token_data("transfer.api.globus.org")
        authorizer = RefreshTokenAuthorizer(
            transfer_tokens["refresh_token"],
            AUTH_CLIENT,
            access_token=transfer_tokens["access_token"],
            expires_at=transfer_tokens["expires_at_seconds"],
        )
        transfer_client = TransferClient(authorizer=authorizer)
    except GlobusAPIError as error:
        print(f"Failed to create Transfer API client: {error.message}")
        sys.exit(1)

    # Instantiate Groups client
    try:
        groups_tokens = token_file_adapter.get_token_data("groups.api.globus.org")
        authorizer = RefreshTokenAuthorizer(
            groups_tokens["refresh_token"],
            AUTH_CLIENT,
            access_token=groups_tokens["access_token"],
            expires_at=groups_tokens["expires_at_seconds"],
        )
        groups_client = GroupsClient(authorizer=authorizer)
    except GlobusAPIError as error:
        print(f"Failed to create Groups API client: {error.message}")
        sys.exit(1)

    return transfer_client, groups_client


def get_endpoint_data():
    endpoints = load_data_from_file("dme_data.json")
    for endpoint in endpoints:
        print(f"-- Endpoint #: {endpoint['index']}")
        print(f"Name: {endpoint['name']}")
        print(f"ID: {endpoint['id']}")
        print(f"Default SOURCE path: {endpoint['paths']['source']}")
        print(f"Default DEST path: {endpoint['paths']['dest']}")
        print("Writable: " + ("True" if endpoint["writable"] == 1 else "False") + "\n")


def get_dme_endpoint(endpoint_number):
    DME_ENDPOINTS = load_data_from_file("dme_data.json")

    # Get DME endpoint UUID
    try:
        endpoint = next(
            ep for ep in DME_ENDPOINTS if int(ep["index"]) == endpoint_number
        )
    except StopIteration as error:
        print(
            f"DME endpoint #{endpoint_number} not found; ensure endpoint index exists in dme_data.json"
        )
        sys.exit(1)

    return endpoint


def get_endpoint(source_dest=None, args=None):
    if source_dest == "SOURCE":
        if args.nondmesource:
            # Ensure non-DME endpoint is a valid UUID
            print(args.nondmesource)
            if validate_endpoint_id(args.nondmesource):
                endpoint_id = args.nondmesource
            path = args.sourcepath
        else:
            # Get source DME endpoint data
            dme_endpoint = get_dme_endpoint(endpoint_number=int(args.source))
            endpoint_id = dme_endpoint["id"]
            path = dme_endpoint["paths"]["source"] + args.dataset

    else:
        if args.nondmedest:
            # Ensure non-DME endpoint is a valid UUID
            if validate_endpoint_id(args.nondmedest):
                endpoint_id = args.nondmedest
            path = args.destpath
        else:
            # Get destination DME endpoint data
            dme_endpoint = get_dme_endpoint(endpoint_number=int(args.dest))
            endpoint_id = dme_endpoint["id"]
            if dme_endpoint["writable"] == 1:
                path = (
                    dme_endpoint["paths"]["dest"]
                    if ("dest" in dme_endpoint["paths"])
                    else ""
                ) + (args.destpath if args.destpath else f"dme_{str(uuid.uuid4())}")
            else:
                path = args.destpath if args.destpath else f"dme_{str(uuid.uuid4())}"

    return endpoint_id, path


def submit_transfer(args=None):
    # Get handles to Globus services
    transfer_client, groups_client = get_globus_service_clients(args=args)

    # Check user's membership in the DME Endpoint Access group
    validate_group_membership(groups_client)

    # Get endpoint ID and path
    try:
        source_endpoint_id, source_path = get_endpoint(source_dest="SOURCE", args=args)
        dest_endpoint_id, dest_path = get_endpoint(source_dest="DEST", args=args)

        print(
            f"Source endpoint name: \
{transfer_client.get_endpoint(source_endpoint_id)['display_name']}"
        )
        print(f"Source path: {source_path}")
        print(
            f"Destination endpoint name: \
{transfer_client.get_endpoint(dest_endpoint_id)['display_name']}"
        )
        print(f"Destination path: {dest_path}")
    except AuthAPIError as error:
        print("Globus Auth API Error: Failed to get endpoint(s)")
        print("Delete 'dme-tokens.json' and run again to re-authenticate.")
        sys.exit(1)

    validate_endpoint_path(transfer_client, source_endpoint_id, source_path)
    validate_endpoint_path(
        transfer_client, dest_endpoint_id, dest_path, create_dest=True
    )

    # Create and submit the transfer task
    tdata = TransferData(
        transfer_client,
        source_endpoint_id,
        dest_endpoint_id,
        label=args.label if args.label else TRANSFER_LABEL,
    )
    tdata.add_item(source_path, dest_path, recursive=True)
    task = transfer_client.submit_transfer(tdata)

    url = "https://app.globus.org/file-manager?" + six.moves.urllib.parse.urlencode(
        {
            "origin_id": source_endpoint_id,
            "origin_path": source_path,
            "destination_id": dest_endpoint_id,
            "destination_path": dest_path,
        }
    )

    # Show user info on transfer task
    print(f"Submitted transfer: {task['task_id']}")
    print(
        f"Get transfer details by running: ./rundme status --task-id {task['task_id']}"
    )
    print(f"Visit the link below to see the changes: {url}")


def get_task_status(args=None):
    # Get handles to Globus services
    transfer_client, groups_client = get_globus_service_clients(args=args)

    try:
        task_details = transfer_client.get_task(args.taskid)
    except GlobusAPIError as error:
        print(f"Failed to get task status: {error.message}")
        sys.exit(1)

    print(task_details)


### EOF
