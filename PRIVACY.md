# Lilbot Privacy Notes

Lilbot is local-first.

## Local Operation

Core Lilbot commands run on the customer machine. The Pro audit and launch-pack workflows inspect files under the configured workspace root and produce local terminal or Markdown output.

## Payment Provider

If Lilbot Pro is sold through Stripe, Gumroad, Lemon Squeezy, Paddle, or another provider, that provider handles checkout data under its own privacy policy.

## License Files

Local license activation stores a license file at:

```text
~/.config/lilbot/license.json
```

The path can be changed with `LILBOT_LICENSE_PATH`. Managed environments may use `LILBOT_LICENSE_KEY` instead of a local activation file.

## Support

Support requests may include command output from `lilbot doctor`, `lilbot self-test`, or `lilbot license status`. Customers should redact private paths, project names, and source snippets before sending support logs.
