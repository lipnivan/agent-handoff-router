from __future__ import annotations

import argparse
import json
import sys

from .config import DEFAULT_CONFIG_PATH, dump_example_config, load_config
from .messages import MessageError, parse_message
from .router import Router


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="handoff-router")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status")

    scan = subparsers.add_parser("scan")
    scan.add_argument("--once", action="store_true")
    scan.add_argument("--route", action="store_true")
    scan.add_argument("--no-pull", action="store_true")
    scan.add_argument("--include-legacy", action="store_true")
    scan.add_argument("--include-routed", action="store_true")

    route = subparsers.add_parser("route")
    route.add_argument("path")

    messages = subparsers.add_parser("messages")
    messages.add_argument("--json", action="store_true")

    validate = subparsers.add_parser("validate")
    validate.add_argument("path")

    init_config = subparsers.add_parser("init-config")
    init_config.add_argument("--path", default=str(DEFAULT_CONFIG_PATH))

    subparsers.add_parser("self-check")
    return parser


def cmd_status(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    router = Router(config)
    inventory = (
        router.message_inventory()
        if config.handoff_repo_dir.exists()
        else {
            "messages": [],
            "pending_messages": 0,
            "routed_messages": 0,
            "legacy_ignored": 0,
            "parse_errors": 0,
        }
    )
    state_exists = config.state_file.exists()
    print(f"config: {args.config}")
    print(f"handoff_repo_path: {config.handoff_repo_path}")
    print(f"handoff_repo_exists: {config.handoff_repo_dir.exists()}")
    print(f"state_path: {config.state_path}")
    print(f"state_exists: {state_exists}")
    print(f"dry_run: {config.dry_run}")
    print(f"messages: {len(inventory['messages'])}")
    print(f"pending_messages: {inventory['pending_messages']}")
    print(f"routed_messages: {inventory['routed_messages']}")
    print(f"legacy_ignored: {inventory['legacy_ignored']}")
    print(f"parse_errors: {inventory['parse_errors']}")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    router = Router(config)
    results = router.scan(
        route=args.route,
        pull=not args.no_pull,
        include_legacy=args.include_legacy,
        include_routed=args.include_routed,
    )
    for result in results:
        print(json.dumps(result.to_dict(), sort_keys=True))
    if args.route and any(result.status == "failed" and result.action == "preflight" for result in results):
        return 1
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    router = Router(config)
    result = router.route_path(args.path)
    print(json.dumps(result.to_dict(), sort_keys=True))
    return 0 if result.status in {"routed", "skipped"} else 1


def cmd_messages(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    if config.handoff_repo_dir.exists():
        router = Router(config)
        payload = router.message_inventory()
    else:
        payload = {
            "messages": [],
            "pending_messages": 0,
            "routed_messages": 0,
            "legacy_ignored": 0,
            "parse_errors": 0,
            "errors": [],
            "legacy": [],
        }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for message in payload["messages"]:
            print(f"{message['type']}\t{message['path']}")
        for error in payload["errors"]:
            print(f"ERROR\t{error['path']}\t{error['error']}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        message = parse_message(args.path)
    except MessageError as exc:
        print(f"invalid: {exc}")
        return 1
    print(json.dumps(message.to_summary(), sort_keys=True))
    return 0


def cmd_init_config(args: argparse.Namespace) -> int:
    path = dump_example_config(args.path)
    print(path)
    return 0


def cmd_self_check(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    router = Router(config)
    report = router.preflight_report()
    for name, check in report.to_dict().items():
        line = f"{name}: {check['status']}"
        if "detail" in check:
            line += f" ({check['detail']})"
        print(line)
    return 0 if report.routing_ok() else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command_map = {
        "status": cmd_status,
        "scan": cmd_scan,
        "route": cmd_route,
        "messages": cmd_messages,
        "validate": cmd_validate,
        "init-config": cmd_init_config,
        "self-check": cmd_self_check,
    }
    return command_map[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
