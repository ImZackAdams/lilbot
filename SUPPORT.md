# Lilbot Pro Support

## Support Promise

Pro customers get setup, activation, and paid-workflow support for Lilbot Pro.

Target first response:

- 1 business day for activation failures
- 2 business days for install, model, or audit issues
- Best effort for unsupported operating systems, unusual hardware, or modified forks

## Customer Intake

Ask customers to include:

```bash
lilbot --version
lilbot doctor
lilbot self-test
lilbot license status
```

For Pro audit issues, also ask for:

```bash
lilbot pro audit .
```

Customers should redact private paths, organization names, or source snippets before sending logs.

## Activation Issues

1. Confirm the customer ran `lilbot license activate <license-key>`.
2. Ask for `lilbot license status`.
3. Confirm `LILBOT_LICENSE_PATH` points to a writable location if they use a managed environment.
4. Reissue a key with `python scripts/issue_license.py --payload <ORDERID>` if the original fulfillment email was malformed.

## Refund Guidance

Refund first-time customers inside 14 days when:

- the key cannot activate after support
- the paid command cannot run in a supported local Python environment
- the customer bought the wrong seat count and immediately repurchases the correct one

Do not promise refunds for revenue outcomes. Lilbot can improve launch readiness, but it cannot guarantee sales.
