#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -f "$REPO_ROOT/_build_dependencies.sh" ]; then
    source "$REPO_ROOT/_build_dependencies.sh"
elif [ -f "_build_dependencies.sh" ]; then
    source "_build_dependencies.sh"
fi

if [ -z "$SPACEMANDMM_TAG" ]; then
    export SPACEMANDMM_TAG="suite-1.11"
fi

wget -O ~/dmdoc "https://github.com/SpaceManiac/SpacemanDMM/releases/download/$SPACEMANDMM_TAG/dmdoc"
chmod +x ~/dmdoc
~/dmdoc --version
