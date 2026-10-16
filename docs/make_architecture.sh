#!/bin/bash
# Render docs/architecture.dot to docs/architecture.svg (needs graphviz and python3). The logos
# are embedded in the SVG, so it displays on its own (GitHub shows README images in an <img>,
# which does not load files an SVG links to).
set -euo pipefail
cd "$(dirname "$0")"
REPO_URL=${REPO_URL:-https://github.com/teknoman117/lekiwi_ros2_ws/}
# the QR code in the title links to the repository (needs qrencode)
qrencode -l M -m 1 -s 8 -o assets/repo_qr.png "$REPO_URL"
dot -Tsvg -Gimagepath=assets/logos:assets architecture.dot | python3 -c '
import base64, mimetypes, os, re, sys
def embed(m):
    path = m.group(2)
    for d in ("assets/logos", "assets"):
        if not os.path.exists(path) and os.path.exists(os.path.join(d, path)):
            path = os.path.join(d, path)
    data = base64.b64encode(open(path, "rb").read()).decode()
    return f"{m.group(1)}=\"data:{mimetypes.guess_type(path)[0]};base64,{data}\""
sys.stdout.write(re.sub(r"(xlink:href|href)=\"([^\"#][^\"]*\.(?:png|svg))\"", embed, sys.stdin.read()))
' > architecture.svg
echo "wrote $PWD/architecture.svg"
