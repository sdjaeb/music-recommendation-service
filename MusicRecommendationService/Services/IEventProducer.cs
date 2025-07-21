namespace MusicRecommendationService.Services;

public interface IEventProducer : IDisposable
{
    void Produce(string topic, string message);
}