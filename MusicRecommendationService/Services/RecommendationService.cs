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
        var cfSongsTask = _minioService.ReadLatestDeltaTableAsync<SongSimilarity>("data", "silver/song_collaborative_filtering");
        var trendingTracksTask = _minioService.ReadLatestDeltaTableAsync<TrendingTrack>("data", "silver/weekly_trending_tracks");
        var userFollowsTask = _minioService.ReadLatestDeltaTableAsync<UserFollow>("data", "bronze/graph_user_follows");
        var listeningHistoryTask = _minioService.ReadLatestDeltaTableAsync<ListeningEvent>("data", "bronze/fact_listening_events");

        await Task.WhenAll(similarSongsTask, cfSongsTask, trendingTracksTask, userFollowsTask, listeningHistoryTask);

        var similarSongs = await similarSongsTask;
        var cfSongs = await cfSongsTask;
        var trendingTracks = await trendingTracksTask;
        var userFollows = await userFollowsTask;
        var listeningHistory = await listeningHistoryTask;

        // 2. Create efficient lookups to avoid repeatedly scanning large lists.
        var userHistoryLookup = listeningHistory.ToLookup(e => e.user_id);
        var userLikedTracks = userHistoryLookup[userId].Where(e => e.event_type == "like").Select(e => e.track_id).ToHashSet();

        if (!userLikedTracks.Any())
        {
            _logger.LogWarning("User {UserId} has no liked tracks. Cannot generate personalized recommendations.", userId);
            return Enumerable.Empty<long>();
        }

        // 3. Calculate scores for all potential candidates
        var recommendationScores = new Dictionary<long, double>();

        // Helper to apply scores from different models
        void ApplyScores(IEnumerable<(long trackId, double score)> candidates)
        {
            foreach (var (trackId, score) in candidates)
            {
                recommendationScores[trackId] = recommendationScores.GetValueOrDefault(trackId, 0) + score;
            }
        }

        // a. Collaborative Filtering Model (Users who liked this also liked...)
        var cfLookup = this.BuildSimilarityLookup(cfSongs);
        var cfCandidates = userLikedTracks
            .SelectMany(likedTrack => cfLookup.GetValueOrDefault(likedTrack, new List<(long, double)>()))
            .Select(c => (c.Item1, c.Item2 * _settings.ModelWeights.CollaborativeFiltering));
        ApplyScores(cfCandidates);

        // b. Playlist-based Similarity Model
        var playlistSimilarityLookup = this.BuildSimilarityLookup(similarSongs);
        var playlistCandidates = userLikedTracks
            .SelectMany(likedTrack => playlistSimilarityLookup.GetValueOrDefault(likedTrack, new List<(long, double)>()))
            .Select(c => (c.Item1, c.Item2 * _settings.ModelWeights.Similarity));
        ApplyScores(playlistCandidates);

        // c. Social Model (songs liked by followed users)
        var followedUserIds = userFollows.Where(f => f.user_id == userId).Select(f => f.follows_user_id).ToHashSet();
        if (followedUserIds.Any())
        {
            var socialCandidates = listeningHistory
                .Where(e => followedUserIds.Contains(e.user_id) && e.event_type == "like")
                .Select(e => (e.track_id, _settings.ModelWeights.Social));
            ApplyScores(socialCandidates);
        }

        // d. Trending Model (Global Popularity)
        if (trendingTracks.Any())
        {
            long maxPlayCount = trendingTracks.Max(t => t.play_count);
            if (maxPlayCount > 0)
            {
                var trendingCandidates = trendingTracks.Select(t => (t.track_id, ((double)t.play_count / maxPlayCount) * _settings.ModelWeights.Trending));
                ApplyScores(trendingCandidates);
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
        var similarityLookup = this.BuildSimilarityLookup(similarSongs);

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

    public async Task<IEnumerable<long>> GetCollaborativeRecommendationsAsync(int userId, int count = 10)
    {
        _logger.LogInformation("Generating collaborative filtering recommendations for user {UserId}", userId);

        // 1. Fetch collaborative filtering data and user listening history
        var cfSongsTask = _minioService.ReadLatestDeltaTableAsync<SongSimilarity>("data", "silver/song_collaborative_filtering");
        var listeningHistoryTask = _minioService.ReadLatestDeltaTableAsync<ListeningEvent>("data", "bronze/fact_listening_events");

        await Task.WhenAll(cfSongsTask, listeningHistoryTask);

        var cfSongs = await cfSongsTask;
        var listeningHistory = await listeningHistoryTask;

        // 2. Get the user's liked tracks
        var userLikedTracks = listeningHistory
            .Where(e => e.user_id == userId && e.event_type == "like")
            .Select(e => e.track_id)
            .ToHashSet();

        if (!userLikedTracks.Any())
        {
            _logger.LogWarning("User {UserId} has no liked tracks to base collaborative filtering recommendations on.", userId);
            return Enumerable.Empty<long>();
        }

        // 3. Pre-build a lookup for faster access.
        var similarityLookup = this.BuildSimilarityLookup(cfSongs);

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

    private Dictionary<long, List<(long otherTrack, double score)>> BuildSimilarityLookup(IEnumerable<SongSimilarity> similarities)
    {
        var lookup = new Dictionary<long, List<(long, double)>>();
        foreach (var s in similarities)
        {
            if (!lookup.ContainsKey(s.track_id_1)) lookup[s.track_id_1] = new List<(long, double)>();
            if (!lookup.ContainsKey(s.track_id_2)) lookup[s.track_id_2] = new List<(long, double)>();
            lookup[s.track_id_1].Add((s.track_id_2, (double)s.score));
            lookup[s.track_id_2].Add((s.track_id_1, (double)s.score));
        }
        return lookup;
    }
}
