# Lilbot Monetization Playbook

Lilbot is packaged as an open-core CLI product.

## Offer

- Free: local chat, deterministic repository/log/system tools, setup diagnostics, and shell-command explanations
- Pro: product-readiness audits for repositories
- Price: $19/month per seat or $190/year

## Launch Checklist

1. Create a Stripe Payment Link, Gumroad product, Lemon Squeezy checkout, Paddle checkout, or billing page for Lilbot Pro.
2. Set `LILBOT_CHECKOUT_URL` to that checkout URL in release docs, support snippets, and managed deployments.
3. Replace the placeholder checkout URL in `site/index.html` before publishing the static sales page.
4. Review `CUSTOMER_TERMS.md`, `SUPPORT.md`, and `PRIVACY.md` before accepting paid customers.
5. Run `python scripts/issue_license.py` for each buyer or wire the same key format into your fulfillment system.
6. Send the buyer their license key and activation command:

```bash
lilbot license activate <license-key>
```

7. Ask the buyer to confirm access:

```bash
lilbot license status
lilbot pro audit .
lilbot pro launch-pack . --output lilbot-launch-pack.md
```

## First Paid Workflow

`lilbot pro audit .` scans a repository and reports:

- buyer-facing positioning
- packaging readiness
- onboarding and diagnostics
- test coverage signals
- release automation gaps
- checkout and license surfaces
- support readiness
- config hygiene
- safety messaging

The command returns a score, findings, launch priorities, and a revenue path.

`lilbot pro launch-pack . --output lilbot-launch-pack.md` turns the same scan into a customer-ready Markdown dossier with checkout copy, a demo script, a fulfillment email, a 48-hour launch plan, and a risk register.

## Fulfillment Notes

The built-in license key format is an MVP local entitlement gate for a CLI product. It is enough to sell and support early customers without adding a hosted billing dependency to the app runtime.

For higher-volume sales, replace manual key delivery with payment-provider webhooks and a private license service while keeping the CLI commands stable:

```bash
lilbot pricing
lilbot license activate <license-key>
lilbot pro audit .
```
