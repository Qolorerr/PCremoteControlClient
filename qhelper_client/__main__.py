import logging
import socket
import sys
from argparse import ArgumentParser, Namespace
import requests

from .config import PATH, SIGN_UP_PATH, GET_TOKEN_PATH, SHOW_AVAILABLE_PC_PATH
from .config import DEVICE_TYPE
from .managed_device_client import ManagedClient
from .managing_device_client import ManagingClient
from .storekeeper import Storekeeper


store_keeper = Storekeeper()

logger = logging.getLogger("app")


def _on_server_error(error: Exception) -> None:
    logger.info(f"Server error {error}")
    print(f"Server error {error}\n")
    sys.exit()


def sign_up(args: Namespace) -> None:
    json = {"login": args.login, "email": args.email, "password": args.password}
    try:
        response = requests.post(f'http://{PATH}{SIGN_UP_PATH}', json=json)
    except Exception as e:
        _on_server_error(e)
    if response.status_code == 201:
        print("Signed up successfully\n")
        logger.info(f"Signed up, login: {args.login}, email: {args.email}")
        get_token(args)
    else:
        message = response.headers['message'] if 'message' in response.headers else ''
        logger.info(f"Error due signing up, login: {args.login}, email: {args.email}, code: {response.status_code}")
        print(f"Error due signing up: {response.status_code} {message}\n")


def sign_in(args: Namespace) -> None:
    get_token(args)


def get_token(args: Namespace) -> None:
    pc_name = socket.gethostname()
    json = {"login_or_email": args.login, "password": args.password, "name": pc_name, "type": DEVICE_TYPE}
    try:
        response = requests.get(f'http://{PATH}{GET_TOKEN_PATH}', json=json)
    except Exception as e:
        _on_server_error(e)
    if response.status_code == 201 and 'token' in response.headers:
        store_keeper.add_token(response.headers['token'])
        logger.info(f"Got new token, login/email: {args.login}")
        print("Got new token\n")
    else:
        message = response.headers['message'] if 'message' in response.headers else ''
        logger.info(f"Error due getting token, login/email: {args.login}, code: {response.status_code}")
        print(f"Error due getting token: {response.status_code} {message}\n")


def run(args: Namespace) -> None:
    if args.manage is None:
        client = ManagedClient(store_keeper)
    else:
        client = ManagingClient(store_keeper, str(args.manage))
    client.run()


def show_available_pc(args: Namespace) -> None:
    token = store_keeper.get_token()
    if token is None:
        print("Token is required\n")
        return
    json = {"token": token}
    try:
        response = requests.get(f'http://{PATH}{SHOW_AVAILABLE_PC_PATH}', json=json)
    except Exception as e:
        _on_server_error(e)
    json = response.json()
    if response.status_code == 200 and 'devices' in json:
        logger.debug(f"Got new list of available pc")
        print("Available devices:\n")
        for device in json['devices']:
            print(f"{device['id']}\t{device['name']}\n")
    else:
        message = response.headers['message'] if 'message' in response.headers else ''
        logger.info(f"Error due showing devices, code: {response.status_code}")
        print(f"Error due showing devices: {response.status_code} {message}\n")


if __name__ == "__main__":
    arg_parser = ArgumentParser()
    subparsers = arg_parser.add_subparsers(help='Methods')

    if not store_keeper.check_existence():
        store_keeper.init()

    if not store_keeper.get_token():
        sign_up_parser = subparsers.add_parser('sign_up', help='Create new account')
        sign_up_parser.add_argument('-login', type=str, help='Your unique name', required=True)
        sign_up_parser.add_argument('-email', type=str, help='Your email', required=True)
        sign_up_parser.add_argument('-password', type=str, help='Your password', required=True)
        sign_up_parser.set_defaults(func=sign_up)

        sign_in_parser = subparsers.add_parser('sign_in', help='Sign in')
        sign_in_parser.add_argument('-login', type=str, help='Your login or email', required=True)
        sign_in_parser.add_argument('-password', type=str, help='Your password', required=True)
        sign_in_parser.set_defaults(func=sign_in)
    else:
        run_parser = subparsers.add_parser('run', help="Run qhelper client")
        run_parser.add_argument('-manage', type=int, help='Id of managing device')
        run_parser.set_defaults(func=run)

        show_available_pc_parser = subparsers.add_parser('show_pc', help="Show available pc (For managing device)")
        show_available_pc_parser.set_defaults(func=show_available_pc)

    args = arg_parser.parse_args()
    try:
        args.func(args)
    except AttributeError:
        print("Use qhelper_client -h\n")
