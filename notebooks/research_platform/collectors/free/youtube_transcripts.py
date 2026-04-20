"""
collectors/free/youtube_transcripts.py
────────────────────────────────────────
YouTube transcript extraction for analyst commentary.
Source: youtube-transcript-api (no API key needed for public videos)
Channels: CNBC TV18, ET Now, Zerodha, well-known analyst channels
"""
from __future__ import annotations
from datetime import date
from typing import Optional
from loguru import logger
from collectors.base import BaseCollector, CollectionResult
from database.connection import get_session
from database.models import EarningsTranscript, Event
from database.queries import upsert_event

# Public YouTube channel IDs for Indian financial content
CHANNELS = {
    "ET Now":       "UCHqeNBs-gF2pCCGbvJFMnHQ",
    "CNBC TV18":    "UCZlBzMlUkU6C0ZmDUoLOPZg",
    "Zerodha":      "UC5WsYMXYhCJMWUwIhj7pcuA",
}
# Known analyst video IDs to track (seed list — add more over time)
SEED_VIDEO_IDS = [
    # These are examples; replace with real video IDs of analyst content
]

class YouTubeTranscriptsCollector(BaseCollector):
    source_name = "youtube_transcripts"
    fallback_chain = ["api", "cache"]

    def _try_api(self, target_date: Optional[date] = None) -> Optional[CollectionResult]:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, VideoUnavailable
        except ImportError:
            logger.warning("[youtube] youtube-transcript-api not installed. Run: pip install youtube-transcript-api")
            return None

        records = []
        today = target_date or date.today()

        # Try to get transcripts for seed video IDs
        for video_id in SEED_VIDEO_IDS[:5]:
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "hi"])
                full_text = " ".join([t["text"] for t in transcript_list])
                if len(full_text) < 100:
                    continue

                # Store as EarningsTranscript for AI pipeline
                with get_session() as s:
                    rec = EarningsTranscript(
                        ticker="MARKET",
                        quarter=f"{today.year}-YT",
                        transcript_text=full_text[:10000],
                        source_url=f"https://youtube.com/watch?v={video_id}",
                        call_date=today,
                    )
                    s.add(rec)
                records.append(rec)
                logger.info(f"[youtube] Transcript stored for {video_id} ({len(full_text)} chars)")
            except (NoTranscriptFound, VideoUnavailable) as e:
                logger.debug(f"[youtube] {video_id}: {e}")
            except Exception as e:
                logger.warning(f"[youtube] {video_id} failed: {e}")

        if not records:
            # Store a placeholder event so the collector shows as "run"
            logger.info("[youtube] No seed videos configured — add video IDs to SEED_VIDEO_IDS")
            return CollectionResult(
                source_name=self.source_name, records=[], status="partial", method_used="api"
            )

        self._store_cache(records, target_date=target_date)
        return CollectionResult(source_name=self.source_name, records=records, status="ok", method_used="api")
