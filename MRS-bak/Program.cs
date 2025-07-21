using MusicRecommendationService.Services;
using Prometheus;
using Serilog;

var builder = WebApplication.CreateBuilder(args);

Log.Logger = new LoggerConfiguration()
  .ReadFrom.Configuration(builder.Configuration)
  .CreateLogger();
builder.Host.UseSerilog();

// Register services for dependency injection.
builder.Services.AddSingleton<IRecommendationService, RecommendationService>();

var app = builder.Build();

// Add Serilog request logging
app.UseSerilogRequestLogging();

// --- Endpoint Definitions ---
app.MapGet("/", () => "Hello World!");

// GET /recommendations/{trackId}
app.MapGet("/recommendations/{trackId:int}", (int trackId, IRecommendationService recommendationService) => {
  var recs = recommendationService.GetRecommendations(trackId);
  if (recs is null || !recs.Any())
    return Results.NotFound();
  
  return Results.Ok(recs.Take(5));
});

// --- Observability ---
app.UseHttpMetrics();          // Automatically track HTTP metrics
app.MapMetrics("/metrics");    // Expose /metrics endpoint

app.Run();
