using MusicRecommendationService.Services;
using System.Text.Json;
using Prometheus;
using Serilog;

var builder = WebApplication.CreateBuilder(args);

builder.Host.UseSerilog((context, config) => 
    config.ReadFrom.Configuration(context.Configuration));

builder.Services.AddSingleton<IRecommendationService, RecommendationService>();
builder.Services.AddSingleton<IEventProducer, KafkaEventProducer>();

// Add health check services
builder.Services.AddHealthChecks();

var app = builder.Build();

app.UseSerilogRequestLogging();
app.UseHttpMetrics();

app.MapGet("/", () => "Hello from Music Recommendation Service!");

app.MapGet("/recommendations/{trackId:int}", (int trackId, IRecommendationService recommendationService, IEventProducer eventProducer, ILogger<Program> logger) => {
  var recs = recommendationService.GetRecommendations(trackId);
  if (recs is null || !recs.Any())
    return Results.NotFound();

  var recommendations = recs.Take(5).ToList();

  // Create an event payload and produce it to Kafka
  try
  {
      var recommendationEvent = new {
          requestedTrackId = trackId,
          recommendations,
          timestamp = DateTime.UtcNow
      };
      eventProducer.Produce("music_recommendations", JsonSerializer.Serialize(recommendationEvent));
  }
  catch (Exception ex)
  {
      logger.LogError(ex, "Failed to queue recommendation event to Kafka for trackId {TrackId}", trackId);
      // This will now only catch synchronous errors, like the producer's internal buffer being full.
  }
    return Results.Ok(recommendations);
});

// Expose the /health endpoint
app.MapHealthChecks("/health");

app.MapMetrics("/metrics");

app.Run();

// Make Program class public for WebApplicationFactory
public partial class Program { }
