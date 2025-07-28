namespace MusicRecommendationService.Models;

public record TrendingTrack(long track_id, long play_count)
{
    public TrendingTrack() : this(0, 0) { }
}

public record SongSimilarity(long track_id_1, long track_id_2, long score)
{
    public SongSimilarity() : this(0, 0, 0) { }
}

public record UserFollow(int user_id, int follows_user_id)
{
    public UserFollow() : this(0, 0) { }
}

public record ListeningEvent(string event_id, int user_id, long track_id, string event_type, DateTime timestamp)
{
    public ListeningEvent() : this(string.Empty, 0, 0, string.Empty, default) { }
}