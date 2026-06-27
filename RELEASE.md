# Lilbot Release Checklist

Use this checklist before publishing a paid Lilbot release.

## Preflight

```bash
python -m unittest discover -s tests -v
python scripts/launch_check.py
```

## Checkout

1. Replace the placeholder checkout URL in `site/index.html`.
2. Set `LILBOT_CHECKOUT_URL` in release notes and managed deployments.
3. Run a checkout sandbox purchase if the provider supports it.

## License Fulfillment

```bash
python scripts/fulfill_order.py --email buyer@example.com --order-id TESTORDER2026 --payload TESTORDER2026
```

Confirm the generated activation command works:

```bash
LILBOT_LICENSE_PATH=/tmp/lilbot-release-license.json lilbot license activate <license-key> --email buyer@example.com
LILBOT_LICENSE_PATH=/tmp/lilbot-release-license.json lilbot pro audit .
```

## Trial Smoke Test

```bash
LILBOT_LICENSE_PATH=/tmp/lilbot-trial-license.json lilbot license start-trial
LILBOT_LICENSE_PATH=/tmp/lilbot-trial-license.json lilbot pro launch-pack . --output release-launch-pack.md
```

Remove any temporary release artifacts before committing.

## Release Notes

Include:

- install command
- upgrade command
- checkout URL
- trial command
- activation command
- support email
- known limitations

## Support Readiness

Confirm that `CUSTOMER_TERMS.md`, `SUPPORT.md`, and `PRIVACY.md` match the current paid offer.
