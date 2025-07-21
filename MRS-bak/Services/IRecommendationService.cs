namespace MusicRecommendationService.Services;

public interface IRecommendationService
{
    IEnumerable<int>? GetRecommendations(int trackId);
}