import re

with open('js/views/player.js', 'r', encoding='utf-8') as f:
    content = f.read()

old_stats_logic = '''            const qualityStats = video.getVideoPlaybackQuality();
            const dropped = qualityStats?.droppedVideoFrames || 0;
            const total = qualityStats?.totalVideoFrames || 0;

            if (!lastFrameStats) {
                lastFrameStats = { dropped, total };
                return;
            }

            const droppedDelta = dropped - lastFrameStats.dropped;
            const totalDelta = total - lastFrameStats.total;
            lastFrameStats = { dropped, total };

            const sampledFrames = droppedDelta + totalDelta;
            if (sampledFrames < 45) return;'''

new_stats_logic = '''            const qualityStats = video.getVideoPlaybackQuality();
            const dropped = qualityStats?.droppedVideoFrames || 0;
            const total = qualityStats?.totalVideoFrames || 0;
            const currentTime = video.currentTime || 0;

            if (!lastFrameStats) {
                lastFrameStats = { dropped, total, time: currentTime };
                return;
            }

            const droppedDelta = dropped - lastFrameStats.dropped;
            const totalDelta = total - lastFrameStats.total;
            const timeDelta = currentTime - lastFrameStats.time;
            lastFrameStats = { dropped, total, time: currentTime };

            if (totalDelta === 0 && timeDelta > 1.5) {
                this._maybeAutoRequestRepair('video_frozen_desync');
                softResync();
                return;
            }

            const sampledFrames = droppedDelta + totalDelta;
            if (sampledFrames < 45) return;'''

content = content.replace(old_stats_logic, new_stats_logic)

old_drift_logic = '''                    const driftSeconds = Math.abs((video.currentTime || 0) - metadata.mediaTime);

                    if (driftSeconds >= DRIFT_SOFT_THRESHOLD_SECONDS) {'''

new_drift_logic = '''                    const driftSeconds = Math.abs((video.currentTime || 0) - metadata.mediaTime);

                    if (driftSeconds >= 0.8) {
                        this._maybeAutoRequestRepair('catastrophic_drift');
                    }

                    if (driftSeconds >= DRIFT_SOFT_THRESHOLD_SECONDS) {'''

content = content.replace(old_drift_logic, new_drift_logic)

with open('js/views/player.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched.")
