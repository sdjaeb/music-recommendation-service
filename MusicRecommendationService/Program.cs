using MusicRecommendationService.Services;
using System.Text.Json;
using MusicRecommendationService.Models;
using Prometheus;
using Serilog;
using Minio.AspNetCore;

var builder = WebApplication.CreateBuilder(args);

builder.Host.UseSerilog((context, config) => 
    config.ReadFrom.Configuration(context.Configuration));

// Add the in-memory cache service
builder.Services.AddMemoryCache();

// The new RecommendationService has dependencies (like MinioClient) that are scoped,
// so it should also be registered as scoped.
builder.Services.AddScoped<IRecommendationService, RecommendationService>();

// Configure strongly-typed settings
builder.Services.Configure<CachingSettings>(builder.Configuration.GetSection(CachingSettings.SectionName));
builder.Services.Configure<RecommendationSettings>(builder.Configuration.GetSection(RecommendationSettings.SectionName));
builder.Services.AddScoped<IMinioService, MinioService>();

// Configure Minio client for dependency injection
builder.Services.AddMinio(configureClient =>
{
    var minioEndpoint = Environment.GetEnvironmentVariable("MINIO_ENDPOINT") ?? "localhost:9000";
    var accessKey = File.ReadAllText(Environment.GetEnvironmentVariable("MINIO_ACCESS_KEY_FILE") ?? string.Empty);
    var secretKey = File.ReadAllText(Environment.GetEnvironmentVariable("MINIO_SECRET_KEY_FILE") ?? string.Empty);

    configureClient.Endpoint = minioEndpoint;
    configureClient.AccessKey = accessKey;
    configureClient.SecretKey = secretKey;
});

builder.Services.AddSingleton<IEventProducer, KafkaEventProducer>(); // For ingestion endpoint

// Add health check services
builder.Services.AddHealthChecks();

var app = builder.Build();

app.UseSerilogRequestLogging();
app.UseHttpMetrics();

app.MapGet("/", () => "Hello from Music Recommendation Service!");

// Helper to reduce duplication for recommendation endpoints
async Task<IResult> HandleRecommendationRequest(
    long userId,
    string notFoundMessage,
    Func<Task<IEnumerable<long>>> recommendationFunc,
    IEventProducer eventProducer,
    ILogger<Program> logger)
{
    var recommendations = (await recommendationFunc()).ToList();

    if (!recommendations.Any())
    {
        return Results.NotFound(new { message = notFoundMessage });
    }

    try
    {
        var recommendationEvent = new RecommendationEvent
        {
            requestedUserId = userId,
            recommendations = recommendations,
            timestamp = DateTime.UtcNow.ToString("o") // ISO 8601 format
        };
        await eventProducer.ProduceAvroAsync("music_recommendations", recommendationEvent);
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "Failed to produce recommendation event to Kafka for user {UserId}", userId);
    }

    return Results.Ok(recommendations);
}

app.MapGet("/recommendations/{userId:int}", 
    (int userId, IRecommendationService recommendationService, IEventProducer eventProducer, ILogger<Program> logger) => 
        HandleRecommendationRequest(userId, $"No recommendations found for user {userId}.", 
            () => recommendationService.GetRecommendationsAsync(userId, 5), eventProducer, logger));

app.MapGet("/recommendations/similar/{userId:int}", 
    (int userId, IRecommendationService recommendationService, IEventProducer eventProducer, ILogger<Program> logger) => 
        HandleRecommendationRequest(userId, $"No similar song recommendations found for user {userId}.", 
            () => recommendationService.GetSimilarRecommendationsAsync(userId, 5), eventProducer, logger));

app.MapGet("/recommendations/collaborative/{userId:int}", 
    (int userId, IRecommendationService recommendationService, IEventProducer eventProducer, ILogger<Program> logger) => 
        HandleRecommendationRequest(userId, $"No collaborative filtering recommendations found for user {userId}.", 
            () => recommendationService.GetCollaborativeRecommendationsAsync(userId, 5), eventProducer, logger));

app.MapGet("/recommendations/trending", 
    (IRecommendationService recommendationService, IEventProducer eventProducer, ILogger<Program> logger) => 
        // Use a sentinel userId of 0 for non-personalized recommendations
        HandleRecommendationRequest(0, "No trending tracks found.", 
            () => recommendationService.GetTrendingRecommendationsAsync(10), eventProducer, logger));

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
