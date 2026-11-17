#!/usr/bin/env bash
# Build the release files for the version in VERSION, from its git tag.
#
#   scripts/release.sh [--tag] [out_dir]      (default out_dir: dist/)
#
# Checks: clean working tree, VERSION looks like 1.2.3, CHANGELOG.md has "## <version>",
# tests pass, and tag v<version> exists and points at HEAD (--tag creates it locally).
# Builds, from the tag (never from the working folder):
#   the-one-skill-<version>.zip         top-level the-one-skill/ folder
#   the-one-skill-<version>.bundle.md   one plain-text file any chat can read
#   notes.md                            this version's CHANGELOG section
# It never pushes or publishes anything: it prints the commands for that.
# Portable: macOS bash 3.2 + BSD tools, and Linux.
set -euo pipefail

TAG_IT=0
OUT=""
for arg in "$@"; do
  case "$arg" in
    --tag) TAG_IT=1 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) OUT=$arg ;;
  esac
done

# Resolve a relative out_dir against where you ran the script, before moving into the repo.
if [ -n "$OUT" ]; then mkdir -p "$OUT" && OUT=$(cd "$OUT" && pwd); fi
REPO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
cd "$REPO"
fail() { echo "release: $*" >&2; exit 1; }

VERSION=$(tr -d '[:space:]' < VERSION)
echo "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || fail "VERSION must look like 1.2.3 (found '$VERSION')"
TAG="v$VERSION"
OUT=${OUT:-"$REPO/dist"}

[ -z "$(git status --porcelain)" ] || fail "working tree has changes; commit or stash them first"
grep -q "^## $VERSION\$" CHANGELOG.md || fail "CHANGELOG.md has no '## $VERSION' section"

echo "Running tests…"
python3 -m unittest discover tests > /dev/null 2>&1 || fail "tests failed (run: python3 -m unittest discover tests)"

if ! git rev-parse -q --verify "refs/tags/$TAG" > /dev/null; then
  if [ "$TAG_IT" = 1 ]; then
    git tag -a "$TAG" -m "the-one-skill $VERSION"
    echo "Created tag $TAG (local only)."
  else
    fail "tag $TAG doesn't exist; run with --tag to create it, or: git tag -a $TAG -m \"the-one-skill $VERSION\""
  fi
fi
[ "$(git rev-parse "$TAG^{commit}")" = "$(git rev-parse HEAD)" ] || fail "tag $TAG doesn't point at HEAD; check out the tag's commit, or bump VERSION"

mkdir -p "$OUT"
ZIP="$OUT/the-one-skill-$VERSION.zip"
BUNDLE="$OUT/the-one-skill-$VERSION.bundle.md"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

git archive --format=zip --prefix=the-one-skill/ -o "$ZIP" "$TAG"
git archive --prefix=the-one-skill/ "$TAG" | tar -x -C "$WORK"
python3 "$WORK/the-one-skill/scripts/bundle.py" pack "$WORK/the-one-skill" -o "$BUNDLE"
awk -v v="## $VERSION" '$0==v{f=1;next} /^## /{f=0} f' CHANGELOG.md > "$OUT/notes.md"

grep -q "^Version: $VERSION\." "$BUNDLE" || fail "bundle header doesn't say version $VERSION"
[ -s "$OUT/notes.md" ] || fail "the CHANGELOG section for $VERSION is empty"

echo
echo "Built from $TAG:"
echo "  $ZIP"
echo "  $BUNDLE"
echo "  $OUT/notes.md"
echo
echo "To publish (nothing has been pushed):"
echo "  git push origin $TAG"
echo "  gh release create $TAG \"$ZIP\" \"$BUNDLE\" --title \"the-one-skill $VERSION\" --notes-file \"$OUT/notes.md\""
echo "Or create the release on GitHub (Releases > Draft a new release), choose tag $TAG, and attach those files."
