using Confluent.Kafka;

namespace MusicRecommendationService.Services;

public class KafkaEventProducer : IEventProducer
{
    private readonly IProducer<Null, string> _producer;
    private readonly ILogger<KafkaEventProducer> _logger;

    public KafkaEventProducer(IConfiguration configuration, ILogger<KafkaEventProducer> logger)
    {
        _logger = logger;
        var config = new ProducerConfig
        {
            BootstrapServers = configuration["KAFKA_BROKER"] ?? "localhost:9092",
            Acks = Acks.Leader, // Only wait for the leader to acknowledge
            MessageTimeoutMs = 5000 // Set a 5-second timeout for message production
        };
        _producer = new ProducerBuilder<Null, string>(config).Build();
        _logger.LogInformation("Kafka producer initialized for broker: {BootstrapServers}", config.BootstrapServers);
    }

    public void Produce(string topic, string message)
    {
        // Use the non-blocking Produce method with a delivery handler (callback).
        // This fires the message and returns immediately. The result is handled in the background.
        _producer.Produce(topic, new Message<Null, string> { Value = message }, (deliveryReport) =>
        {
            if (deliveryReport.Error.Code != ErrorCode.NoError)
            {
                _logger.LogError("Failed to deliver message: {Reason}", deliveryReport.Error.Reason);
            }
            else
            {
                _logger.LogInformation("Produced message to {Topic} partition {Partition} at offset {Offset}",
                    deliveryReport.Topic, deliveryReport.Partition, deliveryReport.Offset);
            }
        });
    }

    public void Dispose()
    {
        _producer.Dispose();
    }
}