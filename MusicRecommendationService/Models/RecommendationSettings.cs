namespace MusicRecommendationService.Models;

public class RecommendationSettings
{
    public const string SectionName = "Recommendation";
    public ModelWeightsSettings ModelWeights { get; set; } = new();
}

public class ModelWeightsSettings
{
    public double Similarity { get; set; } = 0.6;
    public double Trending { get; set; } = 0.2;
    public double Social { get; set; } = 0.5;
}