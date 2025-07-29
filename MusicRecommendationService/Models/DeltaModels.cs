using System.Text.Json.Serialization;

namespace MusicRecommendationService.Models;

// Models for deserializing the _delta_log JSON transaction files

public class DeltaTransaction
{
    [JsonPropertyName("add")]
    public DeltaAdd? Add { get; set; }

    [JsonPropertyName("remove")]
    public DeltaRemove? Remove { get; set; }
}

public class DeltaAdd
{
    [JsonPropertyName("path")]
    public string Path { get; set; } = string.Empty;
}

public class DeltaRemove
{
    [JsonPropertyName("path")]
    public string Path { get; set; } = string.Empty;
}

// Model for deserializing the _delta_log Parquet checkpoint files
public class DeltaCheckpointAction
{
    [JsonPropertyName("add")]
    public DeltaAdd? Add { get; set; }
}