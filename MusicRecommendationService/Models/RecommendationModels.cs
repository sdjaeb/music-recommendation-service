namespace MusicRecommendationService.Models;

public record TrendingTrack(long track_id, long play_count);

public record SongSimilarity(long track_id_1, long track_id_2, long score);