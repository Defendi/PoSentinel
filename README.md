# PoSentinel

[![PyPI version](https://img.shields.io/pypi/v/posentinel.svg)](https://pypi.org/project/posentinel/)
[![Python versions](https://img.shields.io/pypi/pyversions/posentinel.svg)](https://pypi.org/project/posentinel/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Odoo Translation Quality Analyzer** — Protect your Odoo translations before they hit production.

---

## Overview

PoSentinel is a deterministic linter and quality engine designed to inspect `.po` localization files, with first-class support for Odoo modules and terms (`pt_BR` and multilingual setups).

It catches critical runtime translation issues such as corrupted or altered Python format placeholders (`%s`, `%(name)s`), broken HTML/XML tags, empty translations, and uninspected fuzzy entries.

## Quick Start

### Installation

```bash
pip install posentinel
```

### Basic Usage

Analyze a single `.po` file:

```bash
posentinel scan path/to/pt_BR.po
```

Analyze an entire directory or Odoo module structure:

```bash
posentinel scan ./addons/my_module/i18n
```

Export issues in JSON format (ideal for CI/CD integrations):

```bash
posentinel scan pt_BR.po --format json
```

## Exit Codes for CI/CD

- `0`: Scan passed successfully without blocking issues.
- `1`: Validation issues detected (errors found).
- `2`: Runtime error or invalid arguments/configuration.

## License

MIT License. See [LICENSE](LICENSE) for details.
