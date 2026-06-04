"""
Operational CLI for wiring up Tripp's Typeform via API token.

Usage (token can be passed with --token or via TYPEFORM_TOKEN env var):

  # 1. See which forms the token can access (find the form_id)
  python -m scripts.setup_webhook list-forms --token tfp_xxx

  # 2. Dump the field refs of the survey (confirm the 80 questions/refs)
  python -m scripts.setup_webhook list-fields --token tfp_xxx --form ABC123

  # 3. Register the webhook + generate a signing secret
  python -m scripts.setup_webhook create --token tfp_xxx --form ABC123 \
         --url https://your-app.up.railway.app/webhooks/typeform

  # 4. Inspect / remove
  python -m scripts.setup_webhook inspect --token tfp_xxx --form ABC123
  python -m scripts.setup_webhook delete  --token tfp_xxx --form ABC123

After `create`, copy the printed secret into the server's TYPEFORM_WEBHOOK_SECRET
env var (Railway dashboard) so signature verification passes.
"""
from __future__ import annotations

import argparse
import os
import sys

from app.services.typeform_client import TypeformClient, TypeformError

TAG = "assessment-engine"


def _token(args) -> str:
    tok = args.token or os.environ.get("TYPEFORM_TOKEN", "")
    if not tok:
        sys.exit("No token. Pass --token or set TYPEFORM_TOKEN.")
    return tok


def cmd_list_forms(args):
    with TypeformClient(_token(args)) as tf:
        forms = tf.list_forms()
    if not forms:
        print("No forms found for this token.")
        return
    print(f"{len(forms)} form(s):")
    for f in forms:
        print(f"  {f.get('id'):24}  {f.get('title','(untitled)')}")


def cmd_list_fields(args):
    with TypeformClient(_token(args)) as tf:
        fields = tf.list_field_refs(args.form)
    print(f"{len(fields)} field(s) in form {args.form}:")
    for fld in fields:
        print(f"  ref={fld['ref'] or '(none)':20}  type={fld['type']:16}  {fld['title'][:60]}")


def cmd_create(args):
    with TypeformClient(_token(args)) as tf:
        result = tf.upsert_webhook(args.form, url=args.url, tag=TAG, secret=args.secret)
    print("Webhook registered.")
    print(f"  form_id : {args.form}")
    print(f"  url     : {args.url}")
    print(f"  tag     : {result['tag']}")
    print("\n  >>> SET THIS ON THE SERVER (Railway env var):")
    print(f"  TYPEFORM_WEBHOOK_SECRET={result['secret']}")
    print("\n  Without this env var set, signed submissions will be rejected (401).")


def cmd_inspect(args):
    with TypeformClient(_token(args)) as tf:
        wh = tf.get_webhook(args.form, tag=TAG)
    print("Current webhook:")
    for k in ("id", "form_id", "tag", "url", "enabled", "verify_ssl"):
        if k in wh:
            print(f"  {k:10}: {wh[k]}")


def cmd_delete(args):
    with TypeformClient(_token(args)) as tf:
        tf.delete_webhook(args.form, tag=TAG)
    print(f"Webhook '{TAG}' deleted from form {args.form}.")


def main():
    p = argparse.ArgumentParser(description="Tripp Typeform webhook setup")
    p.add_argument("--token", help="Typeform personal access token (or TYPEFORM_TOKEN env)")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("list-forms"); s.set_defaults(func=cmd_list_forms)

    s = sub.add_parser("list-fields"); s.add_argument("--form", required=True)
    s.set_defaults(func=cmd_list_fields)

    s = sub.add_parser("create")
    s.add_argument("--form", required=True)
    s.add_argument("--url", required=True, help="https URL of /webhooks/typeform")
    s.add_argument("--secret", default=None, help="optional; auto-generated if omitted")
    s.set_defaults(func=cmd_create)

    s = sub.add_parser("inspect"); s.add_argument("--form", required=True)
    s.set_defaults(func=cmd_inspect)

    s = sub.add_parser("delete"); s.add_argument("--form", required=True)
    s.set_defaults(func=cmd_delete)

    args = p.parse_args()
    try:
        args.func(args)
    except TypeformError as e:
        sys.exit(f"\nTypeform API error: {e}")
    except ValueError as e:
        sys.exit(f"\nError: {e}")


if __name__ == "__main__":
    main()
