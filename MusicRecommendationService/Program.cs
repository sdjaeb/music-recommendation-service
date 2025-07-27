using MusicRecommendationService.Services;
using MusicRecommendationService.Services;
using System.Text.Json;
using Prometheus;
using Serilog;
using Minio;

var builder = WebApplication.CreateBuilder(args);

builder.Host.UseSerilog((context, config) => 
    config.ReadFrom.Configuration(context.Configuration));

// Add the in-memory cache service
builder.Services.AddMemoryCache();

// The new RecommendationService has dependencies (like MinioClient) that are scoped,
// so it should also be registered as scoped.
builder.Services.AddScoped<IRecommendationService, RecommendationService>();
builder.Services.AddScoped<IMinioService, MinioService>();

// Configure Minio client for dependency injection
builder.Services.AddMinio(configureClient =>
{
    var minioEndpoint = Environment.GetEnvironmentVariable("MINIO_ENDPOINT") ?? "localhost:9000";
    var accessKey = File.ReadAllText(Environment.GetEnvironmentVariable("MINIO_ACCESS_KEY_FILE") ?? string.Empty);
    var secretKey = File.ReadAllText(Environment.GetEnvironmentVariable("MINIO_SECRET_KEY_FILE") ?? string.Empty);

    configureClient.WithEndpoint(minioEndpoint).WithCredentials(accessKey, secretKey).WithSSL(false);
});

builder.Services.AddSingleton<IEventProducer, KafkaEventProducer>(); // For ingestion endpoint

// Add health check services
builder.Services.AddHealthChecks();

var app = builder.Build();

app.UseSerilogRequestLogging();
app.UseHttpMetrics();

app.MapGet("/", () => "Hello from Music Recommendation Service!");

app.MapGet("/recommendations/{trackId:int}", async (int trackId, IRecommendationService recommendationService, IEventProducer eventProducer, ILogger<Program> logger) => {
  var recommendations = (await recommendationService.GetRecommendationsAsync(trackId, 5)).ToList();
  
  if (!recommendations.Any())
  {
      return Results.NotFound(new { message = $"No recommendations found for track {trackId}." });
  }

  // Create an event payload and produce it to Kafka
  try
  {
      var recommendationEvent = new {
          requestedTrackId = trackId,
          recommendations = recommendations,
          timestamp = DateTime.UtcNow
      };
      eventProducer.Produce("music_recommendations", JsonSerializer.Serialize(recommendationEvent));
  }
  catch (Exception ex)
  {
      logger.LogError(ex, "Failed to produce recommendation event to Kafka for trackId {TrackId}", trackId);
  }
    return Results.Ok(recommendations);
});

// New endpoint to ingest user listening events
app.MapPost("/ingest/listening-event", (object listeningEvent, IEventProducer eventProducer, ILogger<Program> logger) => {
    try
    {
        // We accept 'object' and re-serialize to pass it directly to Kafka
        var eventJson = JsonSerializer.Serialize(listeningEvent);
        eventProducer.Produce("user_listening_history", eventJson);
        return Results.Accepted();
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "Failed to ingest listening event.");
        return Results.Problem("An error occurred while processing the event.", statusCode: 500);
    }
});

// Expose the /health endpoint
app.MapHealthChecks("/health");

app.MapMetrics("/metrics");

app.Run();

// Make Program class public for WebApplicationFactory
public partial class Program { }
