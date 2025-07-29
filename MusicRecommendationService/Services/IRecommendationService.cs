namespace MusicRecommendationService.Services;

public interface IRecommendationService
{
    Task<IEnumerable<long>> GetRecommendationsAsync(int userId, int count = 10);
    Task<IEnumerable<long>> GetSimilarRecommendationsAsync(int userId, int count = 10);
    Task<IEnumerable<long>> GetTrendingRecommendationsAsync(int count = 10);
}