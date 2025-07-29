namespace MusicRecommendationService.Models;

public static class RecommendationEventSchema
{
    public const string AvroSchema = """
    {
      "type": "record",
      "name": "RecommendationEvent",
      "namespace": "com.harman.music",
      "fields": [
        { "name": "requestedUserId", "type": "long" },
        {
          "name": "recommendations",
          "type": { "type": "array", "items": "long" }
        },
        { "name": "timestamp", "type": "string" }
      ]
    }
    """;
}