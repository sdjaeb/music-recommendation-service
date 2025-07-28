using System.Collections.Concurrent;
using System.Text.Json;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Options;
using Minio;
using Minio.DataModel.Args;
using MusicRecommendationService.Models;
using Parquet;
using Parquet.Serialization;

namespace MusicRecommendationService.Services;

public interface IMinioService
{
    Task<List<T>> ReadLatestDeltaTableAsync<T>(string bucket, string tablePath) where T : new();
}

public class MinioService : IMinioService
{
    private readonly IMinioClient _minioClient;
    private readonly IMemoryCache _memoryCache;
    private readonly CachingSettings _cachingSettings;
    private readonly ILogger<MinioService> _logger;

    private const string CacheKeyPrefix = "delta-table";

    public MinioService(IMinioClient minioClient, IMemoryCache memoryCache, IOptions<CachingSettings> cachingSettings, ILogger<MinioService> logger)
    {
        _minioClient = minioClient;
        _memoryCache = memoryCache;
        _cachingSettings = cachingSettings.Value;
        _logger = logger;
    }

    public async Task<List<T>> ReadLatestDeltaTableAsync<T>(string bucket, string tablePath) where T : new()
    {
        string cacheKey = $"{CacheKeyPrefix}-{bucket}-{tablePath}";

        // 1. Try to get the data from the cache
        if (_memoryCache.TryGetValue(cacheKey, out List<T>? cachedData))
        {
            _logger.LogInformation("Cache hit for {CacheKey}. Returning {Count} records from cache.", cacheKey, cachedData?.Count ?? 0);
            return cachedData ?? new List<T>();
        }

        _logger.LogInformation("Cache miss for {CacheKey}. Fetching data from MinIO.", cacheKey);

        try
        {
            var allRecords = await FetchDeltaTableFromMinio<T>(bucket, tablePath);

            // Store the newly fetched data in the cache with a configurable expiration time
            var cacheEntryOptions = new MemoryCacheEntryOptions()
                .SetAbsoluteExpiration(TimeSpan.FromHours(_cachingSettings.DeltaTable.DurationHours));

            _memoryCache.Set(cacheKey, allRecords, cacheEntryOptions);
            _logger.LogInformation("Data for {CacheKey} stored in cache. Contains {Count} records.", cacheKey, allRecords.Count);

            return allRecords;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to read delta table {TablePath} from bucket {Bucket}", tablePath, bucket);
            return new List<T>(); // Important: Do not cache on failure
        }
    }

    /// <summary>
    /// Orchestrates fetching and reading all active Parquet files for a given Delta table.
    /// </summary>
    private async Task<List<T>> FetchDeltaTableFromMinio<T>(string bucket, string tablePath) where T : new()
    {
        var deltaLogPath = $"{tablePath}/_delta_log/";
        var parquetFiles = await GetActiveParquetFiles(bucket, deltaLogPath);

        if (!parquetFiles.Any())
        {
            _logger.LogWarning("No active parquet files found for table {TablePath} in bucket {Bucket}", tablePath, bucket);
            return new List<T>();
        }

        _logger.LogInformation("Found {Count} parquet files to process for table {TablePath}", parquetFiles.Count, tablePath);

        // Read parquet files in parallel for better performance
        var allRecords = new ConcurrentBag<T>();
        var readTasks = parquetFiles.Select(async filePath =>
        {
            var records = await ReadParquetFileAsync<T>(bucket, $"{tablePath}/{filePath}");
            foreach (var record in records)
            {
                allRecords.Add(record);
            }
        });
        await Task.WhenAll(readTasks);

        return allRecords.ToList();
    }

    /// <summary>
    /// Reads a single Parquet file from MinIO and deserializes it into a collection of objects.
    /// </summary>
    private async Task<IEnumerable<T>> ReadParquetFileAsync<T>(string bucket, string objectPath) where T : new()
    {
        using var fileStream = new MemoryStream();
        await _minioClient.GetObjectAsync(new GetObjectArgs()
                .WithBucket(bucket)
                .WithObject(objectPath)
                .WithCallbackStream(stream => stream.CopyTo(fileStream))
        );
        fileStream.Position = 0;

        // Parquet.Net can deserialize directly into a list of objects.
        return await ParquetSerializer.DeserializeAsync<T>(fileStream);
    }

    /// <summary>
    /// Reads the Delta Lake transaction log to find the list of active Parquet files.
    /// This implementation correctly handles checkpoint files for performance and correctness.
    /// </summary>
    private async Task<List<string>> GetActiveParquetFiles(string bucket, string deltaLogPath)
    {
        var logFiles = await ListLogDirectoryAsync(bucket, deltaLogPath);
        if (!logFiles.Any()) return new List<string>();

        var lastCheckpointPath = logFiles
            .Where(f => f.EndsWith(".checkpoint.parquet"))
            .OrderByDescending(GetVersionFromPath)
            .FirstOrDefault();

        var activeFiles = new HashSet<string>();
        long lastCheckpointVersion = -1;

        if (lastCheckpointPath != null)
        {
            _logger.LogInformation("Found checkpoint file: {CheckpointPath}", lastCheckpointPath);
            lastCheckpointVersion = GetVersionFromPath(lastCheckpointPath);
            var checkpointActions = await ReadParquetFileAsync<DeltaCheckpointAction>(bucket, lastCheckpointPath);
            foreach (var action in checkpointActions.Where(a => a.Add != null))
            {
                activeFiles.Add(action.Add!.Path);
            }
        }
        else
        {
            _logger.LogInformation("No checkpoint file found. Processing all JSON logs.");
        }

        var subsequentJsonLogs = logFiles
            .Where(f => f.EndsWith(".json"))
            .Select(f => new { Path = f, Version = GetVersionFromPath(f) })
            .Where(f => f.Version > lastCheckpointVersion)
            .OrderBy(f => f.Version)
            .Select(f => f.Path);

        foreach (var logPath in subsequentJsonLogs)
        {
            await ApplyJsonLog(bucket, logPath, activeFiles);
        }

        return activeFiles.ToList();
    }

    /// <summary>
    /// Lists all files within a given prefix in a MinIO bucket.
    /// </summary>
    private async Task<List<string>> ListLogDirectoryAsync(string bucket, string prefix)
    {
        var files = new List<string>();
        var listArgs = new ListObjectsArgs().WithBucket(bucket).WithPrefix(prefix).WithRecursive(true);

        var listObjectsTask = new TaskCompletionSource<List<string>>();
        _minioClient.ListObjectsAsync(listArgs).Subscribe(
            item => files.Add(item.Key),
            ex => listObjectsTask.SetException(ex),
            () => listObjectsTask.SetResult(files)
        );

        return await listObjectsTask.Task;
    }

    /// <summary>
    /// Reads a single Delta transaction log file and applies its 'add' and 'remove' actions to the
    /// current set of active files.
    /// </summary>
    private async Task ApplyJsonLog(string bucket, string logFilePath, ISet<string> activeFiles)
    {
        var getObjectArgs = new GetObjectArgs()
            .WithBucket(bucket)
            .WithObject(logFilePath)
            .WithCallbackStream((stream) =>
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
                    if (transaction?.Remove?.Path != null)
                    {
                        activeFiles.Remove(transaction.Remove.Path);
                    }
                }
            });

        await _minioClient.GetObjectAsync(getObjectArgs);
    }

    private long GetVersionFromPath(string path)
    {
        var fileName = Path.GetFileName(path);
        var versionString = fileName.Split('.').First();
        return long.TryParse(versionString, out var version) ? version : -1;
    }
}