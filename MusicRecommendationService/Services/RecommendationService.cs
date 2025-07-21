using MusicRecommendationService.Models;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace MusicRecommendationService.Services;

public class RecommendationService : IRecommendationService
{
    // A simple data structure to hold our listening history
    private readonly List<ListeningEvent> _listeningHistory;
    private readonly ILookup<int, int> _userListenHistoryLookup;

    public RecommendationService(IHostEnvironment hostEnvironment)
    {
        var historyJsonPath = Path.Combine(hostEnvironment.ContentRootPath, "Data", "listening_history.json");
        var historyJson = File.ReadAllText(historyJsonPath);
        _listeningHistory = JsonSerializer.Deserialize<List<ListeningEvent>>(historyJson, new JsonSerializerOptions { PropertyNameCaseInsensitive = true }) ?? new List<ListeningEvent>();

        // Create a lookup for efficient access to a user's listening history
        _userListenHistoryLookup = _listeningHistory.ToLookup(e => e.UserId, e => e.TrackId);
    }

    public IEnumerable<int>? GetRecommendations(int trackId)
    {
        // --- Simple Collaborative Filtering Logic ---

        // 1. Find other users who also liked or completed listening to the given track.
        var similarUserIds = _listeningHistory
            .Where(e => e.TrackId == trackId && (e.EventType == "like" || e.EventType == "complete_listen"))
            .Select(e => e.UserId)
            .Distinct()
            .Take(20) // Limit to a smaller group for performance
            .ToList();

        if (!similarUserIds.Any())
        {
            return null; // No one else has liked this track, can't recommend anything.
        }

        // 2. Find all the other tracks that these similar users have liked or completed.
        var potentialRecommendations = _listeningHistory
            .Where(e => similarUserIds.Contains(e.UserId) && (e.EventType == "like" || e.EventType == "complete_listen"))
            .Select(e => e.TrackId)
            .Distinct()
            .Where(t => t != trackId); // Exclude the original track

        // 3. Return the most popular tracks among that group.
        return potentialRecommendations
            .GroupBy(t => t)
            .OrderByDescending(g => g.Count())
            .Select(g => g.Key);
    }
}

// A simple record to model our listening events
public record ListeningEvent(int UserId, int TrackId, string EventType, DateTime Timestamp);
