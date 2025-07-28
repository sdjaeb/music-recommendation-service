using System.Text.Json.Serialization;

namespace MusicRecommendationService.Models;

public class UserAnalyticsSummary
{
    [JsonPropertyName("user_id")] public long UserId { get; set; }
    [JsonPropertyName("total_likes_count")] public long TotalLikesCount { get; set; }
    [JsonPropertyName("relevant_likes_count")] public long RelevantLikesCount { get; set; }
}