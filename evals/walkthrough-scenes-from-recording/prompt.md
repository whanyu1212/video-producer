---
tags: [video-producer, walkthrough, scenes, footage, no-credits]
max_turns: 80
timeout_seconds: 2400
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Turn recording.mp4 into a narrated 16:9 walkthrough of our task board app. The voice-over is already recorded: narration.mp3, with its word timings in narration.words.json and its text in script.txt. The recording shows the board, then an open card, then the share dialog; keep each screen up while the voice talks about it. Put a label on screen as each of these is said: Board, Notes, History, Share. Add captions too. Put the project in this folder and show me a still of each label's moment to approve. Don't do the full render yet.

Input files: recording.mp4, narration.mp3, narration.words.json, script.txt
