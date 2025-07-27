using MusicRecommendationService.Models;

namespace MusicRecommendationService.Services;

public class RecommendationService : IRecommendationService
{
    private readonly ILogger<RecommendationService> _logger;
    private readonly IMinioService _minioService;

    // --- Hybrid Model Weights (from ROADMAP.md) ---
    private const double SimilarityWeight = 0.7;
    private const double TrendingWeight = 0.3;

    public RecommendationService(ILogger<RecommendationService> logger, IMinioService minioService)
    {
        _logger = logger;
        _minioService = minioService;
    }

    public async Task<IEnumerable<long>> GetRecommendationsAsync(int trackId, int count = 10)
    {
        _logger.LogInformation("Generating hybrid recommendations for track {TrackId}", trackId);

        // 1. Fetch analytical data from MinIO concurrently
        var similarSongsTask = _minioService.ReadLatestDeltaTableAsync<SongSimilarity>("data", "silver/song_similarity_by_playlist");
        var trendingTracksTask = _minioService.ReadLatestDeltaTableAsync<TrendingTrack>("data", "silver/weekly_trending_tracks");

        await Task.WhenAll(similarSongsTask, trendingTracksTask);

        var similarSongs = await similarSongsTask;
        var trendingTracks = await trendingTracksTask;

        if (!similarSongs.Any() && !trendingTracks.Any())
        {
            _logger.LogWarning("No similarity or trending data available. Cannot generate recommendations.");
            return Enumerable.Empty<long>();
        }

        // 2. Calculate scores for all potential candidates
        var recommendationScores = new Dictionary<long, double>();

        // a. Add candidates from song similarity (Playlist Co-occurrence)
        var similarityCandidates = similarSongs.Where(s => s.track_id_1 == trackId || s.track_id_2 == trackId);
        foreach (var candidate in similarityCandidates)
        {
            long similarTrackId = candidate.track_id_1 == trackId ? candidate.track_id_2 : candidate.track_id_1;
            recommendationScores[similarTrackId] = recommendationScores.GetValueOrDefault(similarTrackId, 0) + (candidate.score * SimilarityWeight);
        }

        // b. Add candidates from trending tracks (Popularity-Based)
        long maxPlayCount = trendingTracks.Any() ? trendingTracks.Max(t => t.play_count) : 1;
        foreach (var track in trendingTracks)
        {
            double normalizedScore = (double)track.play_count / maxPlayCount;
            recommendationScores[track.track_id] = recommendationScores.GetValueOrDefault(track.track_id, 0) + (normalizedScore * TrendingWeight);
        }

        // 3. Rank and return top recommendations, excluding the input track
        return recommendationScores
            .Where(kvp => kvp.Key != trackId)
            .OrderByDescending(kvp => kvp.Value)
            .Select(kvp => kvp.Key)
            .Take(count);
    }
}
