#!/usr/bin/env bash
set -euo pipefail

demo_edit_dir="$(cd "$(dirname "$0")" && pwd -P)"
patch_dir="$demo_edit_dir/patch"
source_video="$demo_edit_dir/final-before-body-fix.mp4"

mkdir -p "$patch_dir"
if [[ ! -f "$source_video" ]]; then
  cp "$demo_edit_dir/final.mp4" "$source_video"
fi

ffmpeg -y -loglevel error -i "$source_video" \
  -vf "trim=end_frame=1086,setpts=PTS-STARTPTS,fps=30,format=yuv420p" \
  -an -c:v libx264 -preset medium -crf 18 -movflags +faststart \
  "$patch_dir/pre.mp4"

ffmpeg -y -loglevel error -i "$demo_edit_dir/06-body-corrected.webm" \
  -vf "fps=30,scale=1280:720:flags=lanczos,trim=end_frame=269,setpts=N/(30*TB),format=yuv420p" \
  -an -c:v libx264 -preset medium -crf 18 -movflags +faststart \
  "$patch_dir/body-base.mp4"

.venv/bin/python "$demo_edit_dir/burn-captions.py" \
  "$patch_dir/body-base.mp4" "$demo_edit_dir/body-caption.srt" \
  "$patch_dir/body-captioned.mp4"

ffmpeg -y -loglevel error -i "$source_video" \
  -vf "trim=start_frame=1355,setpts=PTS-STARTPTS,fps=30,format=yuv420p" \
  -an -c:v libx264 -preset medium -crf 18 -movflags +faststart \
  "$patch_dir/post.mp4"

ffmpeg -y -loglevel error \
  -f concat -safe 0 -i "$demo_edit_dir/patch-segments.txt" -c copy \
  "$demo_edit_dir/final-body-fix.mp4"
