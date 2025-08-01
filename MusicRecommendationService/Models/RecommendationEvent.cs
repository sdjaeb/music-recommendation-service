namespace MusicRecommendationService.Models;

public class RecommendationEvent
{
    // Property names match the Avro schema fields for automatic mapping.
    public long requestedUserId { get; set; }
    public List<long> recommendations { get; set; }
    public string timestamp { get; set; }
}