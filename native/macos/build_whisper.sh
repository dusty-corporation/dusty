#!/usr/bin/env bash
# Local pinned sources only. CMake may modify only the recipe-owned source copy.
set -euo pipefail
export LC_ALL=C GIT_OPTIONAL_LOCKS=0
fail() { echo "$1" >&2; exit 1; }
[[ $# -eq 3 || $# -eq 4 ]] ||
  fail 'Usage: build_whisper.sh <source-checkout> <new-output-directory> <cpu|metal> [macos-deployment-target]'
backend="$3"
case "$backend" in cpu) metal=OFF;; metal) metal=ON;; *) fail 'Unknown Mac backend';; esac
# Lowest macOS that every output supports (ADR 0032 amendment). ggml-blas calls the
# Accelerate cblas_sgemm interface selected by ACCELERATE_NEW_LAPACK, which exists
# only on macOS 13.3 and newer and is not guarded at run time. Metal features that
# need newer systems (residency sets, the tensor API, bfloat) are guarded at run time.
deployment="${4:-13.3}"
[[ "$deployment" =~ ^[1-9][0-9]\.[0-9]$ ]] || fail 'Invalid macOS deployment target'
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
pin() {
  awk -v want="[$1]" -v key="$2" '
    $0 == want { section=1; next }
    /^\[/ { section=0 }
    section && $1 == key && $2 == "=" { gsub(/"/, "", $3); print $3 }
  ' "$repo/native/versions.toml"
}
# The Mac engine has its own complete approved patch; the commit is shared with Windows.
commit="$(pin whisper_cpp commit)"
patch_name="$(pin whisper_cpp_macos patch)"
patch_hash="$(pin whisper_cpp_macos patch_sha256)"
[[ "$commit" =~ ^[0-9a-f]{40}$ && "$patch_hash" =~ ^[0-9a-f]{64}$ && -n "$patch_name" ]] || fail 'Missing source or patch pin'
patch_path="$repo/$patch_name"
[[ "$(shasum -a 256 "$patch_path" | awk '{print $1}')" == "$patch_hash" ]] || fail 'Approved patch hash mismatch'
source_dir="$(cd "$1" && pwd -P)"
source_root="$(git -C "$source_dir" rev-parse --show-toplevel)"
[[ "$(cd "$source_root" && pwd -P)" == "$source_dir" ]] || fail 'Whisper source root mismatch'
[[ "$(git -C "$source_dir" rev-parse HEAD)" == "$commit" ]] || fail 'Whisper commit mismatch'
[[ -z "$(git -C "$source_dir" ls-files --others)" ]] || fail 'Whisper source has untracked additions'
canonical_diff_hash() {
  git -C "$1" -c core.quotePath=true -c diff.algorithm=myers -c diff.mnemonicPrefix=false \
    diff --binary --no-ext-diff --no-textconv --src-prefix=a/ --dst-prefix=b/ \
    --unified=3 --no-color --no-renames --abbrev=7 HEAD -- | shasum -a 256 | awk '{print $1}'
}
input_diff="$(canonical_diff_hash "$source_dir")"
empty_hash=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
case "$input_diff" in
  "$empty_hash") input_state=pristine;;
  "$patch_hash") input_state=approved-patch;;
  *) fail 'Whisper source differs from the complete approved patch';;
esac
[[ -f "$source_dir/CMakeLists.txt" ]] || fail 'Whisper CMake source is missing'
[[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]] || fail 'Native Mac arm64 required'
out_parent="$(cd "$(dirname "$2")" && pwd -P)"
out_name="$(basename "$2")"
[[ "$out_name" != . && "$out_name" != .. ]] || fail 'Output must be a new directory'
out="$out_parent/$out_name"
[[ ! -e "$out" && ! -L "$out" ]] || fail 'Refusing existing output directory'
case "$out/" in "$source_dir/"*) fail 'Output must be outside the source checkout';; esac
clang="$(xcrun --find clang)"
clangxx="$(xcrun --find clang++)"
sdk="$(xcrun --show-sdk-path)"
cmake_tool="$(command -v cmake)"
mkdir "$out"
git -c core.hooksPath=/dev/null clone --no-hardlinks --dissociate --no-checkout \
  -- "$source_dir" "$out/source" > "$out/source-copy.txt" 2>&1
git -C "$out/source" -c core.hooksPath=/dev/null checkout --detach "$commit" >> "$out/source-copy.txt" 2>&1
git -C "$out/source" apply --check "$patch_path"
git -C "$out/source" apply "$patch_path"
[[ "$(canonical_diff_hash "$out/source")" == "$patch_hash" ]] || fail 'Copied source patch closure mismatch'
{
  echo "source_commit=$commit"
  echo "source_tree=$(git -C "$out/source" rev-parse 'HEAD^{tree}')"
  echo "approved_patch_sha256=$patch_hash"
  echo "canonical_source_diff_sha256=$patch_hash"
  echo "caller_source_state=$input_state"
  echo "target=macos-arm64"
  echo "backend=$backend"
  echo "release_banner=1.9.5; patched identity is retained above"
  echo "deployment_target=$deployment"
  echo "file_prefix_map=<output>=/dusty-whisper"
  echo "clang=$clang"
  echo "sdk=$sdk"
  echo "cmake=$cmake_tool"
  uname -a
  sw_vers
  "$clang" --version
  xcrun --show-sdk-version
  "$cmake_tool" --version
} > "$out/provenance.txt"
# Map the per-output absolute path away so __FILE__ strings in ggml asserts do not
# make otherwise identical builds differ by output directory. Any use of an API
# newer than the deployment target that is not guarded at run time fails the build.
flags="-ffile-prefix-map=$out=/dusty-whisper -Werror=unguarded-availability -Werror=unguarded-availability-new"
"$cmake_tool" -S "$out/source" -B "$out/build" \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release \
  "-DCMAKE_C_FLAGS=$flags" "-DCMAKE_CXX_FLAGS=$flags" "-DCMAKE_ASM_FLAGS=-ffile-prefix-map=$out=/dusty-whisper" \
  "-DCMAKE_OSX_DEPLOYMENT_TARGET:STRING=$deployment" \
  -DCMAKE_C_COMPILER="$clang" -DCMAKE_CXX_COMPILER="$clangxx" \
  -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_SYSROOT="$sdk" \
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=@loader_path' \
  -DBUILD_SHARED_LIBS=ON -DWHISPER_BUILD_IS_DEV=OFF \
  -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_EXAMPLES=ON -DWHISPER_BUILD_SERVER=OFF \
  -DWHISPER_CURL=OFF -DWHISPER_SDL2=OFF -DWHISPER_COREML=OFF \
  -DWHISPER_OPENVINO=OFF -DWHISPER_VITISAI=OFF \
  -DGGML_NATIVE=OFF -DGGML_OPENMP=OFF -DGGML_CCACHE=OFF -DGGML_BACKEND_DL=OFF \
  -DGGML_CPU=ON -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=Apple -DGGML_ACCELERATE=ON \
  -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_RPC=OFF \
  -DGGML_METAL="$metal" -DGGML_METAL_EMBED_LIBRARY=ON \
  > "$out/configure-output.txt" 2>&1
for required in \
  "CMAKE_OSX_DEPLOYMENT_TARGET:STRING=$deployment" \
  WHISPER_BUILD_IS_DEV:BOOL=OFF WHISPER_BUILD_SERVER:BOOL=OFF WHISPER_CURL:BOOL=OFF \
  GGML_NATIVE:BOOL=OFF GGML_BACKEND_DL:BOOL=OFF GGML_RPC:BOOL=OFF \
  GGML_CUDA:BOOL=OFF GGML_VULKAN:BOOL=OFF "GGML_METAL:BOOL=$metal"; do
  grep -Fqx "$required" "$out/build/CMakeCache.txt" || fail "Required cache setting missing: $required"
done
"$cmake_tool" --build "$out/build" --target whisper-cli -j 4 > "$out/build-output.txt" 2>&1
mkdir "$out/package"
cp -p "$out/build/bin/whisper-cli" "$out/package/"
for library in "$out/build/bin/"*.dylib; do cp -pP "$library" "$out/package/"; done
cp "$out/source/LICENSE" "$out/package/LICENSE.txt"
file "$out/package/whisper-cli" > "$out/architecture.txt"
otool -L "$out/package/whisper-cli" "$out/package/"*.dylib > "$out/dependencies.txt"
for image in "$out/package/whisper-cli" "$out/package/"*.dylib; do
  [[ -L "$image" ]] && continue
  echo "$(basename "$image"): $(vtool -show-build "$image" | awk '$1 == "minos" { print $2 }')"
done > "$out/minimum-os.txt"
awk -v want="$deployment" '$2 != want { bad=1 } END { exit bad || NR == 0 }' "$out/minimum-os.txt" ||
  fail 'Output minimum macOS differs from the deployment target'
! grep -rqaF "$out" "$out/package" || fail 'Output embeds its build path'
(
  cd "$out/package"
  shasum -a 256 whisper-cli *.dylib LICENSE.txt
) > "$out/SHA256SUMS.txt"
# Prove CMake changed no tracked source beyond the approved patch.
[[ "$(canonical_diff_hash "$out/source")" == "$patch_hash" ]] || fail 'Build changed approved tracked source'
[[ "$(canonical_diff_hash "$source_dir")" == "$input_diff" ]] || fail 'Caller source changed during build'
