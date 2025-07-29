using Confluent.Kafka;
using Confluent.SchemaRegistry;
using Confluent.SchemaRegistry.Serdes;
using MusicRecommendationService.Models;

namespace MusicRecommendationService.Services;

public class KafkaEventProducer : IEventProducer
{
    private readonly IProducer<Null, string> _jsonProducer;
    private readonly IProducer<Null, RecommendationEvent> _avroProducer;
    private readonly ILogger<KafkaEventProducer> _logger;

    public KafkaEventProducer(IConfiguration configuration, ILogger<KafkaEventProducer> logger)
    {
        _logger = logger;
        var bootstrapServers = configuration["KAFKA_BROKER"] ?? "localhost:9092";

        // --- Configure JSON Producer (for existing string-based events) ---
        var jsonProducerConfig = new ProducerConfig
        {
            BootstrapServers = bootstrapServers
        };
        _jsonProducer = new ProducerBuilder<Null, string>(jsonProducerConfig).Build();

        // --- Configure Avro Producer (for new schema-based events) ---
        var schemaRegistryConfig = new SchemaRegistryConfig
        {
            Url = configuration["SCHEMA_REGISTRY_URL"] ?? "localhost:8085"
        };
        var avroProducerConfig = new ProducerConfig { BootstrapServers = bootstrapServers };

        var schemaRegistry = new CachedSchemaRegistryClient(schemaRegistryConfig);
        _avroProducer = new ProducerBuilder<Null, RecommendationEvent>(avroProducerConfig)
            .SetValueSerializer(new AvroSerializer<RecommendationEvent>(schemaRegistry))
            .Build();

        _logger.LogInformation("Kafka producers initialized for broker: {BootstrapServers} and Schema Registry: {SchemaRegistryUrl}", 
            bootstrapServers, schemaRegistryConfig.Url);
    }

    public void Produce(string topic, string message)
    {
        _jsonProducer.Produce(topic, new Message<Null, string> { Value = message }, deliveryReport =>
        {
            if (deliveryReport.Error.Code != ErrorCode.NoError)
            {
                _logger.LogError("Failed to deliver JSON message to {Topic}: {Reason}", topic, deliveryReport.Error.Reason);
            }
        });
    }

    public async Task ProduceAvroAsync(string topic, RecommendationEvent message)
    {
        try
        {
            var deliveryResult = await _avroProducer.ProduceAsync(topic, new Message<Null, RecommendationEvent> { Value = message });
            _logger.LogInformation("Produced Avro message to {Topic} partition {Partition} at offset {Offset}",
                deliveryResult.Topic, deliveryResult.Partition, deliveryResult.Offset);
        }
        catch (ProduceException<Null, RecommendationEvent> e)
        {
            _logger.LogError(e, "Failed to deliver Avro message to {Topic}: {Reason}", topic, e.Error.Reason);
        }
    }

    public void Dispose()
    {
        _jsonProducer.Flush(TimeSpan.FromSeconds(10));
        _jsonProducer.Dispose();
        _avroProducer.Flush(TimeSpan.FromSeconds(10));
        _avroProducer.Dispose();
    }
}