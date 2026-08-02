#!/usr/bin/env bash
set -euo pipefail

demo_edit_dir="$(cd "$(dirname "$0")" && pwd -P)"
clip_dir="$demo_edit_dir/clips"
verify_dir="$demo_edit_dir/verify"
mkdir -p "$clip_dir" "$verify_dir"

encode_trim() {
  local input_file="$1"
  local output_file="$2"
  local start_time="$3"
  local duration="$4"
  ffmpeg -y -loglevel error \
    -ss "$start_time" -i "$input_file" -t "$duration" \
    -vf "fps=30,scale=1280:720:flags=lanczos,format=yuv420p" \
    -an -c:v libx264 -preset medium -crf 18 -movflags +faststart \
    "$output_file"
}

encode_still() {
  local frame_file="$1"
  local output_file="$2"
  local duration="$3"
  ffmpeg -y -loglevel error \
    -loop 1 -framerate 30 -i "$frame_file" -t "$duration" \
    -vf "scale=1280:720:flags=lanczos,format=yuv420p" \
    -an -c:v libx264 -preset medium -crf 18 -movflags +faststart \
    "$output_file"
}

ffmpeg -y -loglevel error -ss 0.7 -i "$demo_edit_dir/01-title.webm" \
  -frames:v 1 "$verify_dir/title-frame.png"
ffmpeg -y -loglevel error -ss 0.7 -i "$demo_edit_dir/08-transition.webm" \
  -frames:v 1 "$verify_dir/transition-frame.png"
ffmpeg -y -loglevel error -ss 1.0 -i "$demo_edit_dir/13-end.webm" \
  -frames:v 1 "$verify_dir/end-frame.png"

encode_still "$verify_dir/title-frame.png" "$clip_dir/01-title.mp4" 3.0
encode_trim "$demo_edit_dir/02-search.webm" "$clip_dir/02-search.mp4" 0.6 7.0
encode_trim "$demo_edit_dir/03-candidates.webm" "$clip_dir/03-candidates.mp4" 0.4 8.5
encode_trim "$demo_edit_dir/04-adopt.webm" "$clip_dir/04-adopt.mp4" 0.4 7.0

ffmpeg -y -loglevel error \
  -ss 0.6 -i "$demo_edit_dir/05-draft-start.webm" -t 15.5 \
  -vf "setpts=PTS/1.55,fps=30,scale=1280:720:flags=lanczos,format=yuv420p" \
  -an -c:v libx264 -preset medium -crf 18 -movflags +faststart \
  "$clip_dir/05-draft.mp4"

encode_trim "$demo_edit_dir/06-body.webm" "$clip_dir/06-body.mp4" 0.5 9.0
encode_trim "$demo_edit_dir/07-sources-logo.webm" "$clip_dir/07-sources-logo.mp4" 0.7 13.5
encode_still "$verify_dir/transition-frame.png" "$clip_dir/08-transition.mp4" 2.6
encode_trim "$demo_edit_dir/09-checklist-draft.webm" "$clip_dir/09-checklist-draft.mp4" 0.7 13.5
encode_trim "$demo_edit_dir/10-seven-pages.webm" "$clip_dir/10-seven-pages.mp4" 0.6 14.5
encode_trim "$demo_edit_dir/11-render.webm" "$clip_dir/11-render.mp4" 0.4 8.5
encode_trim "$demo_edit_dir/12-preview-download.webm" "$clip_dir/12-preview-download.mp4" 0.6 12.5
encode_still "$verify_dir/end-frame.png" "$clip_dir/13-end.mp4" 5.2

ffmpeg -y -loglevel error \
  -f concat -safe 0 -i "$demo_edit_dir/segments.txt" -c copy \
  "$demo_edit_dir/raw-concat.mp4"

/Users/cengweiting/Developer/daibu-content-brain/.venv/bin/python \
  "$demo_edit_dir/burn-captions.py" \
  "$demo_edit_dir/raw-concat.mp4" "$demo_edit_dir/master.srt" \
  "$demo_edit_dir/preview.mp4"

cp "$demo_edit_dir/preview.mp4" "$demo_edit_dir/final.mp4"
