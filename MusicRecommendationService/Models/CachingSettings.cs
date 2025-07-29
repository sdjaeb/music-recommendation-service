namespace MusicRecommendationService.Models;

public class CachingSettings
{
    public const string SectionName = "Caching";
    public DeltaTableCachingSettings DeltaTable { get; set; } = new();
}

public class DeltaTableCachingSettings
{
    public double DurationHours { get; set; } = 1.0;
}