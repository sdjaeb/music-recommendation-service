namespace MusicRecommendationService.Models;

public class RecommendationSettings
{
    public const string SectionName = "Recommendation";
    public ModelWeights ModelWeights { get; set; } = new();
}

public class ModelWeights
{
    public double Similarity { get; set; } = 0.6;
    public double Trending { get; set; } = 0.2;
    public double Social { get; set; } = 0.5;
    public double CollaborativeFiltering { get; set; } = 1.5; // Give this a higher weight
}