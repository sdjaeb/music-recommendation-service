using MusicRecommendationService.Models;
using System.Text.Json;

namespace MusicRecommendationService.Services;

public class RecommendationService : IRecommendationService
{
    private readonly Dictionary<int, List<int>> _alsoLikedMap;
    // The 'personas' data is loaded but not currently used in the recommendation logic.
    // private readonly List<Persona> _personas;

    public RecommendationService(IHostEnvironment hostEnvironment)
    {
        var alsoLikedJsonPath = Path.Combine(hostEnvironment.ContentRootPath, "Data", "alsoLiked.json");
        var alsoLikedJson = File.ReadAllText(alsoLikedJsonPath);
        var alsoLikedStringKeyMap = JsonSerializer.Deserialize<Dictionary<string, List<int>>>(alsoLikedJson);

        _alsoLikedMap = alsoLikedStringKeyMap!
            .ToDictionary(kvp => int.Parse(kvp.Key), kvp => kvp.Value);
    }

    public IEnumerable<int>? GetRecommendations(int trackId)
    {
        _alsoLikedMap.TryGetValue(trackId, out var recommendations);
        return recommendations;
    }
}