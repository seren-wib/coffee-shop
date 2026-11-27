# AWS policies for continuous deployment

Templates for SIP 3.6. Replace `<ACCOUNT_ID>` and `<INSTANCE_ID>` before use; the real values stay out of this public repo.

| File | Attached to | Allows |
| --- | --- | --- |
| `github-deploy-trust.json` | IAM role `coffee-shop-github-deploy` (trust policy) | GitHub Actions OIDC tokens from `main` of this repo only |
| `github-deploy-policy.json` | same role (inline policy) | `ssm:SendCommand` with `AWS-RunShellScript` to the one production instance, and reading the result |

The instance itself uses an instance profile with the AWS managed policy `AmazonSSMManagedInstanceCore` so the SSM agent can register. No inbound port is opened for this.
