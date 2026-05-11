---
allowed-tools:
- terminal
- file
author: unknown
description: OpenAI Whisper speech-to-text. Transcribe audio/video files to text.
  Supports 99 languages. Uses system Python 3.12 (torch-based).
execution: manual
name: whisper
trigger:
- transcribe audio/video to text
- generate subtitles/SRT from audio
- translate audio to English
version: 1.0.0
---

# Whisper — Speech-to-Text Transcription

## What It Is

[OpenAI Whisper](https://github.com/openai/whisper) is a general-purpose speech recognition model. Installed at **20250625**.

> ⚠️ **First run downloads the model (~3GB for large-v3).** Run a test first:
> ```bash
> whisper-transcribe --model tiny --language zh /path/to/audio.mp3
> ```

## Usage

### Basic Transcription (Chinese)

```bash
whisper-transcribe audio.mp3 --model base --language zh
```

Output files: `.txt`, `.vtt`, `.srt`, `.tsv`, `.json`

### Translate to English

```bash
whisper-transcribe audio.mp3 --model base --task translate
```

### Specify Output Format

```bash
whisper-transcribe audio.mp3 --model medium --output_format srt
```

### Available Models

| Model | Size | RAM | Speed | Accuracy |
|-------|------|-----|-------|----------|
| tiny | ~1GB | ~1GB | fastest | lowest |
| base | ~1GB | ~1GB | fast | low |
| small | ~2GB | ~2GB | moderate | moderate |
| medium | ~3GB | ~3GB | slow | high |
| large-v3 | ~6GB | ~6GB | slowest | highest |

On this system (8GB RAM, no GPU), recommended: `base` or `small`.

### Batch Processing

```bash
for f in *.mp3; do
  whisper-transcribe "$f" --model base --language zh --output_dir ./transcripts/
done
```

## Integration

- Audio from WeChat voice messages → Whisper → text
- Meeting recordings → Whisper → meeting notes
- Video lectures → Whisper → SRT subtitles

## Pitfalls

- First run downloads model files; choose model size wisely
- CPU-only mode: large-v3 can take 10x real-time on this system
- For long audio (>30min), split into chunks first
- Chinese accuracy: base model works for clear speech; use medium for accented/dialect
