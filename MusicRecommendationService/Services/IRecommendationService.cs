namespace MusicRecommendationService.Services;

public interface IRecommendationService
{
    Task<IEnumerable<long>> GetRecommendationsAsync(int trackId, int count = 10);
}