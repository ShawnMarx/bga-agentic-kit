#!/usr/bin/env bash
# Clone the reference games into ./reference/ (gitignored). Grep them for ground truth before
# trusting the model's memory of a framework API — see docs/framework/README.md.
# These are other people's code under their own licences: read, learn and cite; don't paste.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p reference
clone() { [ -d "reference/$2" ] && git -C "reference/$2" pull -q --ff-only || git clone -q --depth 1 "https://github.com/$1.git" "reference/$2"; echo "reference/$2"; }
clone elaskavaia/bga-heartsla   bga-heartsla     # modern skeleton (PHP state classes) + _ide_helper.php + bga-framework.d.ts
clone AntonioSoler/bga-santorini bga-santorini   # classic layout; one-class-per-ability powers
clone elaskavaia/bga-sharedcode bga-sharedcode   # utilities, animation helpers, kitchen-sink demo
