using System.Text.Json;
using System.Text.Json.Serialization;
using Minio;
using Microsoft.Extensions.Caching.Memory;
using Minio.Exceptions;
using Parquet;
using Parquet.Data;

namespace MusicRecommendationService.Services;

public interface IMinioService
{
    Task<List<T>> ReadLatestDeltaTableAsync<T>(string bucket, string tablePath) where T : new();
}

public class MinioService : IMinioService
{
    private readonly IMinioClient _minioClient;
    private readonly IMemoryCache _memoryCache;
    private readonly ILogger<MinioService> _logger;

    public MinioService(IMinioClient minioClient, IMemoryCache memoryCache, ILogger<MinioService> logger)
    {
        _minioClient = minioClient;
        _memoryCache = memoryCache;
        _logger = logger;
    }

    public async Task<List<T>> ReadLatestDeltaTableAsync<T>(string bucket, string tablePath) where T : new()
    {
        string cacheKey = $"delta-table-{bucket}-{tablePath}";

        // 1. Try to get the data from the cache
        if (_memoryCache.TryGetValue(cacheKey, out List<T>? cachedData))
        {
            _logger.LogInformation("Cache hit for {CacheKey}. Returning {Count} records from cache.", cacheKey, cachedData?.Count ?? 0);
            return cachedData ?? new List<T>();
        }

        _logger.LogInformation("Cache miss for {CacheKey}. Fetching data from MinIO.", cacheKey);

        var allRecords = new List<T>();
        try
        {
            var deltaLogPath = $"{tablePath}/_delta_log/";
            var parquetFiles = await GetActiveParquetFiles(bucket, deltaLogPath);
    
            if (!parquetFiles.Any())
            {
                _logger.LogWarning("No active parquet files found for table {TablePath} in bucket {Bucket}", tablePath, bucket);
                return allRecords;
            }
    
            _logger.LogInformation("Found {Count} parquet files to process for table {TablePath}", parquetFiles.Count, tablePath);
    
            foreach (var filePath in parquetFiles)
            {
                var fullPath = $"{tablePath}/{filePath}";
                var fileStream = new MemoryStream();
    
                var getObjectArgs = new GetObjectArgs()
                    .WithBucket(bucket)
                    .WithObject(fullPath)
                    .WithCallbackStream(stream => stream.CopyTo(fileStream));
    
                await _minioClient.GetObjectAsync(getObjectArgs);
                fileStream.Position = 0;
    
                using var parquetReader = await ParquetReader.CreateAsync(fileStream);
                var data = await parquetReader.ReadAsync<T>();
                allRecords.AddRange(data);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to read delta table {TablePath} from bucket {Bucket}", tablePath, bucket);
            return allRecords; // Important: Do not cache on failure
        }

        // 3. Store the newly fetched data in the cache with an expiration time
        var cacheEntryOptions = new MemoryCacheEntryOptions()
            .SetAbsoluteExpiration(TimeSpan.FromHours(1)); // Cache for 1 hour

        _memoryCache.Set(cacheKey, allRecords, cacheEntryOptions);
        _logger.LogInformation("Data for {CacheKey} stored in cache. Contains {Count} records.", cacheKey, allRecords.Count);

        return allRecords;
    }

    private async Task<List<string>> GetActiveParquetFiles(string bucket, string deltaLogPath)
    {
        var jsonLogs = new List<string>();
        var listArgs = new ListObjectsArgs().WithBucket(bucket).WithPrefix(deltaLogPath).WithRecursive(true);
        
        var observable = _minioClient.ListObjectsAsync(listArgs);
        await foreach (var item in observable)
        {
            if (item.Key.EndsWith(".json"))
            {
                jsonLogs.Add(item.Key);
            }
        }

        if (!jsonLogs.Any()) return new List<string>();

        var latestLog = jsonLogs.OrderByDescending(f => f).First();
        _logger.LogInformation("Reading latest delta transaction log: {LogFile}", latestLog);

        var activeFiles = new List<string>();
        var getObjectArgs = new GetObjectArgs().WithBucket(bucket).WithObject(latestLog);
        
        await _minioClient.GetObjectAsync(getObjectArgs, (stream) =>
        {
            using var reader = new StreamReader(stream);
            string? line;
            while ((line = reader.ReadLine()) != null)
            {
                var transaction = JsonSerializer.Deserialize<DeltaTransaction>(line);
                if (transaction?.Add?.Path != null)
                {
                    activeFiles.Add(transaction.Add.Path);
                }
            }
        });

        return activeFiles;
    }

    // Helper classes for deserializing the _delta_log JSON
    private class DeltaTransaction
    {
        [JsonPropertyName("add")]
        public DeltaAdd? Add { get; set; }
    }

    private class DeltaAdd
    {
        [JsonPropertyName("path")]
        public string Path { get; set; } = string.Empty;
    }
}