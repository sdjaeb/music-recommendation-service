using MusicRecommendationService.Models;

namespace MusicRecommendationService.Services;

public interface IEventProducer : IDisposable
{
    void Produce(string topic, string message);
    Task ProduceAvroAsync(string topic, RecommendationEvent message);
}