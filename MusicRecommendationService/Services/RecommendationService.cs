using MusicRecommendationService.Models;
using Microsoft.Extensions.Options;
using System.Linq;

namespace MusicRecommendationService.Services;

public class RecommendationService : IRecommendationService
{
    private readonly ILogger<RecommendationService> _logger;
    private readonly IMinioService _minioService;
    private readonly RecommendationSettings _settings;

    public RecommendationService(ILogger<RecommendationService> logger, IMinioService minioService, IOptions<RecommendationSettings> settings)
    {
        _logger = logger;
        _minioService = minioService;
        _settings = settings.Value;
    }

    public async Task<IEnumerable<long>> GetRecommendationsAsync(int userId, int count = 10)
    {
        _logger.LogInformation("Generating hybrid recommendations for user {UserId}", userId);

        // 1. Fetch all analytical and source data from MinIO concurrently
        var similarSongsTask = _minioService.ReadLatestDeltaTableAsync<SongSimilarity>("data", "silver/song_similarity_by_playlist");
        var trendingTracksTask = _minioService.ReadLatestDeltaTableAsync<TrendingTrack>("data", "silver/weekly_trending_tracks");
        var userFollowsTask = _minioService.ReadLatestDeltaTableAsync<UserFollow>("data", "bronze/graph_user_follows");
        var listeningHistoryTask = _minioService.ReadLatestDeltaTableAsync<ListeningEvent>("data", "bronze/fact_listening_events");

        await Task.WhenAll(similarSongsTask, trendingTracksTask, userFollowsTask, listeningHistoryTask);

        var similarSongs = await similarSongsTask;
        var trendingTracks = await trendingTracksTask;
        var userFollows = await userFollowsTask;
        var listeningHistory = await listeningHistoryTask;

        // 2. Create efficient lookups to avoid repeatedly scanning large lists.
        // This is a major performance optimization over the previous approach.
        var userHistoryLookup = listeningHistory.ToLookup(e => e.user_id);
        var userLikedTracks = userHistoryLookup[userId].Where(e => e.event_type == "like").Select(e => e.track_id).ToHashSet();
        var userFollowsLookup = userFollows.ToLookup(f => f.user_id, f => f.follows_user_id);

        // 3. Calculate scores for all potential candidates
        var recommendationScores = new Dictionary<long, double>();

        // a. Add candidates from song similarity based on user's history
        // Pre-build a lookup for faster access. This is more efficient than iterating the full list for each liked track.
        var similarityLookup = new Dictionary<long, List<(long otherTrack, long score)>>();
        foreach (var s in similarSongs)
        {
            if (!similarityLookup.ContainsKey(s.track_id_1)) similarityLookup[s.track_id_1] = new List<(long, long)>();
            if (!similarityLookup.ContainsKey(s.track_id_2)) similarityLookup[s.track_id_2] = new List<(long, long)>();
            similarityLookup[s.track_id_1].Add((s.track_id_2, s.score));
            similarityLookup[s.track_id_2].Add((s.track_id_1, s.score));
        }

        foreach (var listenedTrackId in userLikedTracks)
        {
            if (similarityLookup.TryGetValue(listenedTrackId, out var candidates))
            {
                foreach (var (similarTrackId, score) in candidates)
                {
                    recommendationScores[similarTrackId] = recommendationScores.GetValueOrDefault(similarTrackId, 0) + score * _settings.ModelWeights.Similarity;
                }
            }
        }

        // b. Add candidates from social graph (tracks liked by followed users)
        var followedUserIds = userFollowsLookup[userId].ToHashSet();
        if (followedUserIds.Any())
        {
            foreach (var followedId in followedUserIds)
            {
                var followedLikes = userHistoryLookup[followedId].Where(e => e.event_type == "like").Select(e => e.track_id);
                foreach (var trackId in followedLikes)
                {
                    recommendationScores[trackId] = recommendationScores.GetValueOrDefault(trackId, 0) + _settings.ModelWeights.Social;
                }
            }
        }

        // c. Add candidates from trending tracks (Global Popularity) and apply weights
        if (trendingTracks.Any())
        {
            long maxPlayCount = trendingTracks.Max(t => t.play_count);
            if (maxPlayCount > 0)
            {
                foreach (var track in trendingTracks)
                {
                    double normalizedScore = (double)track.play_count / maxPlayCount;
                    recommendationScores[track.track_id] = recommendationScores.GetValueOrDefault(track.track_id, 0) + (normalizedScore * _settings.ModelWeights.Trending);
                }
            }
        }

        // 4. Rank and return top recommendations, excluding tracks the user has already liked
        return recommendationScores
            .Where(kvp => !userLikedTracks.Contains(kvp.Key)) // Don't recommend songs the user already likes
            .OrderByDescending(kvp => kvp.Value)
            .Select(kvp => kvp.Key)
            .Take(count);
    }

    public async Task<IEnumerable<long>> GetSimilarRecommendationsAsync(int userId, int count = 10)
    {
        _logger.LogInformation("Generating song similarity recommendations for user {UserId}", userId);

        // 1. Fetch song similarity and user listening history data
        var similarSongsTask = _minioService.ReadLatestDeltaTableAsync<SongSimilarity>("data", "silver/song_similarity_by_playlist");
        var listeningHistoryTask = _minioService.ReadLatestDeltaTableAsync<ListeningEvent>("data", "bronze/fact_listening_events");

        await Task.WhenAll(similarSongsTask, listeningHistoryTask);

        var similarSongs = await similarSongsTask;
        var listeningHistory = await listeningHistoryTask;

        // 2. Get the user's liked tracks
        var userLikedTracks = listeningHistory
            .Where(e => e.user_id == userId && e.event_type == "like")
            .Select(e => e.track_id)
            .ToHashSet();

        if (!userLikedTracks.Any())
        {
            _logger.LogWarning("User {UserId} has no liked tracks to base recommendations on.", userId);
            return Enumerable.Empty<long>();
        }

        // 3. Pre-build a lookup for faster access.
        var similarityLookup = new Dictionary<long, List<(long otherTrack, long score)>>();
        foreach (var s in similarSongs)
        {
            if (!similarityLookup.ContainsKey(s.track_id_1)) similarityLookup[s.track_id_1] = new List<(long, long)>();
            if (!similarityLookup.ContainsKey(s.track_id_2)) similarityLookup[s.track_id_2] = new List<(long, long)>();
            similarityLookup[s.track_id_1].Add((s.track_id_2, s.score));
            similarityLookup[s.track_id_2].Add((s.track_id_1, s.score));
        }

        // 4. Calculate scores for candidates based on similarity
        var recommendationScores = new Dictionary<long, double>();
        foreach (var listenedTrackId in userLikedTracks)
        {
            if (similarityLookup.TryGetValue(listenedTrackId, out var candidates))
            {
                foreach (var (similarTrackId, score) in candidates)
                {
                    // Use the raw score, not weighted
                    recommendationScores[similarTrackId] = recommendationScores.GetValueOrDefault(similarTrackId, 0) + score;
                }
            }
        }

        // 5. Rank and return top recommendations, excluding tracks the user has already liked
        return recommendationScores
            .Where(kvp => !userLikedTracks.Contains(kvp.Key))
            .OrderByDescending(kvp => kvp.Value)
            .Select(kvp => kvp.Key)
            .Take(count);
    }

    public async Task<IEnumerable<long>> GetTrendingRecommendationsAsync(int count = 10)
    {
        _logger.LogInformation("Generating trending recommendations");

        // 1. Fetch trending tracks data from the silver layer
        var trendingTracks = await _minioService.ReadLatestDeltaTableAsync<TrendingTrack>("data", "silver/weekly_trending_tracks");

        if (!trendingTracks.Any())
        {
            _logger.LogWarning("No trending tracks found in the silver layer.");
            return Enumerable.Empty<long>();
        }

        // 2. The data should already be aggregated by the Spark job.
        // We just need to order and take the top N.
        return trendingTracks
            .OrderByDescending(t => t.play_count)
            .Select(t => t.track_id)
            .Take(count);
    }
}
